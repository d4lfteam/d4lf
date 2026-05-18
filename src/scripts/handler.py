from __future__ import annotations

import logging
import re
import sys
import threading
import time
from contextlib import suppress
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Set as AbstractSet

if sys.platform != "darwin":
    import keyboard

import src.scripts.loot_filter_tts
import src.scripts.vision_mode_fast
import src.scripts.vision_mode_with_highlighting
import src.tts
from src.cam import Cam
from src.config.helper import singleton
from src.config.loader import IniConfigLoader
from src.config.settings_models import (
    IS_HOTKEY_KEY,
    LIVE_RELOAD_GROUP_KEY,
    AdvancedOptionsModel,
    GeneralModel,
    ItemRefreshType,
    VisionModeType,
)
from src.dataloader import Dataloader
from src.loot_mover import move_items_to_inventory, move_items_to_stash
from src.paragon_overlay import request_close, run_paragon_overlay
from src.scripts.common import SETUP_INSTRUCTIONS_URL
from src.ui.char_inventory import CharInventory
from src.ui.stash import Stash
from src.utils.custom_mouse import mouse
from src.utils.process_handler import kill_thread, safe_exit
from src.utils.window import screenshot

LOGGER = logging.getLogger(__name__)

LOCK = threading.Lock()


def _setting_key(section: str, field_name: str) -> str:
    return f"{section}.{field_name}"


def _field_metadata(model_class: type[Any], field_name: str) -> dict[str, Any]:
    return model_class.model_fields[field_name].json_schema_extra or {}


def _collect_reload_group_keys(section: str, model_class: type[Any], group_name: str) -> set[str]:
    return {
        _setting_key(section, field_name)
        for field_name in model_class.model_fields
        if _field_metadata(model_class, field_name).get(LIVE_RELOAD_GROUP_KEY) == group_name
    }


def _collect_hotkey_setting_keys() -> set[str]:
    hotkey_keys = {
        _setting_key("advanced_options", field_name)
        for field_name in AdvancedOptionsModel.model_fields
        if _field_metadata(AdvancedOptionsModel, field_name).get(IS_HOTKEY_KEY) == "True"
    }
    hotkey_keys.update(_collect_reload_group_keys("advanced_options", AdvancedOptionsModel, "hotkeys"))
    return hotkey_keys


def _has_any_changed(changed_keys: AbstractSet[str], relevant_keys: set[str]) -> bool:
    return any(key in changed_keys for key in relevant_keys)


HOTKEY_SETTING_KEYS = _collect_hotkey_setting_keys()
LANGUAGE_SETTING_KEYS = _collect_reload_group_keys("general", GeneralModel, "language")
LOG_LEVEL_SETTING_KEYS = _collect_reload_group_keys("advanced_options", AdvancedOptionsModel, "log_level")
MANUAL_RESTART_SETTING_KEYS = _collect_reload_group_keys("general", GeneralModel, "restart_app")
VISION_MODE_TYPE_SETTING_KEY = _setting_key("general", "vision_mode_type")


@singleton
class InventoryExpTracker:
    def __init__(self):
        self._last_exp_hover_time = 0
        self._exp_hover_active = False

    def on_inventory_open(self):
        """Callback for inventory key to optionally update experience stats."""
        config = IniConfigLoader()
        from src.info_overlay import load_info_settings
        info_config = load_info_settings()
        handler = ScriptHandler()
        if (
            info_config["check_exp_on_inventory_open"]
            and not config.advanced_options.vision_mode_only
            and handler.loot_interaction_thread is None
            and not self._exp_hover_active
        ):
            now = time.time()
            cooldown_s = info_config["exp_age_before_refresh"] * 60
            # Bypass cooldown if experience tracking hasn't been initialized yet
            is_initialized = hasattr(handler, "_last_exp_balance")
            if is_initialized and (now - self._last_exp_hover_time) < cooldown_s:
                return

            def _task():
                try:
                    time.sleep(0.5)
                    _hover_experience_balance()
                    mouse.move(*Cam().abs_window_to_monitor((0, 0)))
                finally:
                    self._exp_hover_active = False

            self._exp_hover_active = True
            self._last_exp_hover_time = time.time()
            threading.Thread(target=_task, daemon=True).start()


@singleton
class ScriptHandler:
    def __init__(self):
        self.loot_interaction_thread = None
        self.paragon_overlay_thread: threading.Thread | None = None
        self.info_overlay_thread: threading.Thread | None = None
        self.did_stop_scripts = False
        self._vision_mode_was_running_before_overlay = False
        self._hotkey_handles: list[Any] = []
        self._runtime_config_lock = threading.RLock()
        self._manual_restart_warning = False
        self._config = IniConfigLoader()
        self._last_info_overlay_toggle = 0
        self._language = self._config.general.language
        self._log_level = self._config.advanced_options.log_lvl.value.upper()
        self.vision_mode = self._create_vision_mode(self._config.general.vision_mode_type)

        # Stats tracking
        self._stats_start_time = None
        self._total_gold_gained = 0
        self._total_exp_gained = 0
        self._pending_gold_value = None
        self._gold_verification_count = 0
        self._max_exp = None
        src.tts.Publisher().subscribe(self._on_tts_data)

        self.setup_key_binds()
        self._config.register_change_listener(self._on_config_changed)
        if self._config.general.run_vision_mode_on_startup:
            self.run_vision_mode()

    def reset_gold_stats(self):
        """Reset session gold totals and baseline."""
        self._total_gold_gained = 0
        if hasattr(self, "_last_gold_balance"):
            delattr(self, "_last_gold_balance")
        self._pending_gold_value = None
        self._gold_verification_count = 0
        LOGGER.info("Gold session stats reset")

    def reset_exp_stats(self):
        """Reset session experience totals and baseline."""
        self._total_exp_gained = 0
        if hasattr(self, "_last_exp_balance"):
            delattr(self, "_last_exp_balance")
        self._pending_gold_value = None
        self._gold_verification_count = 0
        LOGGER.info("Experience session stats reset")

    def _create_vision_mode(self, vision_mode_type: VisionModeType):
        if vision_mode_type == VisionModeType.fast:
            return src.scripts.vision_mode_fast.VisionModeFast()
        return src.scripts.vision_mode_with_highlighting.VisionModeWithHighlighting()

    def _on_tts_data(self, tts_item: list[str]):
        """Callback for TTS data to track gold and experience gains."""
        from src.info_overlay import update_info_stats
        from src.item.descr.read_descr_tts import _create_base_item_from_tts

        if not tts_item or len(tts_item) < 1:
            return

        raw_line = tts_item[0]
        item_name = ""
        val = 0
        mx_val = None

        # Handle Gold statistics from raw TTS string (e.g., '2,225,130,802 Gold')
        if (
            "gold" in raw_line.lower()
            and not any(x in raw_line.lower() for x in ["sell value", "repair", "cost", "price", "buy", "fee", "spent", "purchase"])
            and (match := re.search(r"([0-9,.]+)\s+Gold", raw_line, re.IGNORECASE))
        ):
            item_name = "gold_balance"
            raw_val = re.sub(r"\D", "", match.group(1))
            if not raw_val:
                return
            val = int(raw_val)
        # Handle Experience statistics (e.g., 'Level 209 Experience: 55,843,725 / 74,304,757')
        elif "experience" in raw_line.lower() and (match := re.search(r"Experience:\s+([0-9,.]+)\s+/\s+([0-9,.]+)", raw_line, re.IGNORECASE)):
            item_name = "experience_gain"
            raw_val = re.sub(r"\D", "", match.group(1))
            raw_mx = re.sub(r"\D", "", match.group(2))
            if not raw_val or not raw_mx:
                return
            val = int(raw_val)
            mx_val = int(raw_mx)

        # Fallback to standard item parser if raw string wasn't a recognized stat
        if not item_name:
            if len(tts_item) < 2:
                return
            item = _create_base_item_from_tts(tts_item)
            if not item:
                return
            item_name = item.name
            val = item.power
            mx_val = getattr(item, "max_exp", None)

        if item_name:
            LOGGER.debug(f"TTS Stat parsing result: item_name='{item_name}', val={val}, mx_val={mx_val}")

        if item_name == "gold_balance":
            if not hasattr(self, "_last_gold_balance"):
                self._last_gold_balance = val
                self._pending_gold_value = None
                self._gold_verification_count = 0
                if self._stats_start_time is None:
                    self._stats_start_time = time.time()
                update_info_stats(gph=0, total_gained=0)
                return

            if val == self._last_gold_balance:
                # Reset verification if we match the already confirmed balance
                self._pending_gold_value = None
                self._gold_verification_count = 0
                return

            # Value is different from confirmed balance; check if it matches or exceeds the pending value
            if self._pending_gold_value is not None and val >= self._pending_gold_value:
                self._gold_verification_count += 1
                self._pending_gold_value = val
            else:
                self._pending_gold_value = val
                self._gold_verification_count = 1

            # Confirm change only after 3 consecutive identical scans
            if self._gold_verification_count >= 3:
                # Suspicious Jump: If current balance is > 10x the last one, it was probably a tooltip reset
                if self._last_gold_balance > 0 and val > self._last_gold_balance * 10 and val > 10_000_000:
                    LOGGER.debug(f"Massive gold jump detected ({self._last_gold_balance:,} -> {val:,}). Resetting baseline.")
                    self._last_gold_balance = val
                # Significant Drop: If value is < 1% of balance, it's likely a misread tooltip; ignore but update baseline
                elif val < self._last_gold_balance * 0.01 and self._last_gold_balance > 10_000_000:
                    LOGGER.debug(f"Gold value too low ({val:,} vs {self._last_gold_balance:,}), likely tooltip. Skipping gain.")
                    self._last_gold_balance = val
                else:
                    delta = val - self._last_gold_balance
                    if delta > 0:
                        self._total_gold_gained += delta
                        LOGGER.debug(f"Confirmed gold change: +{delta:,} (New Total Gained: {self._total_gold_gained:,})")

                    elapsed_hours = (time.time() - self._stats_start_time) / 3600.0
                    gph = int(self._total_gold_gained / elapsed_hours) if elapsed_hours > (1/60.0) else 0
                    update_info_stats(gph=gph, total_gained=self._total_gold_gained)
                    self._last_gold_balance = val

                self._pending_gold_value = None
                self._gold_verification_count = 0

        elif item_name == "experience_gain":
            if not hasattr(self, "_last_exp_balance"):
                self._last_exp_balance = val
                self._max_exp = mx_val
                if self._stats_start_time is None:
                    self._stats_start_time = time.time()
                update_info_stats(eph=0, total_exp=0, t2l="-")
                return

            delta = val - self._last_exp_balance
            if delta > 0:
                self._total_exp_gained += delta

            self._last_exp_balance = val
            self._max_exp = mx_val if mx_val is not None else self._max_exp
            elapsed_hours = (time.time() - self._stats_start_time) / 3600.0
            eph = int(self._total_exp_gained / elapsed_hours) if elapsed_hours > (1/60.0) else 0
            t2l = "-"
            if eph > 0 and self._max_exp:
                remaining_xp = self._max_exp - val
                hours = remaining_xp / eph
                t2l = f"{int(hours * 60)}m" if hours < 1 else f"{int(hours)}h {int((hours % 1) * 60)}m"
            update_info_stats(eph=eph, total_exp=self._total_exp_gained, t2l=t2l)

    def _graceful_exit(self):
        safe_exit()

    def _on_config_changed(self, changed_keys: AbstractSet[str]) -> None:
        """Apply relevant settings after a config change event."""
        with self._runtime_config_lock:
            if _has_any_changed(changed_keys, LOG_LEVEL_SETTING_KEYS):
                self._refresh_logging_level(self._config)
            if _has_any_changed(changed_keys, HOTKEY_SETTING_KEYS):
                self._refresh_hotkeys(self._config)
            if _has_any_changed(changed_keys, LANGUAGE_SETTING_KEYS):
                self._refresh_language_assets(self._config)
            if VISION_MODE_TYPE_SETTING_KEY in changed_keys:
                self._notify_manual_restart_required("vision mode changes")
            elif _has_any_changed(changed_keys, MANUAL_RESTART_SETTING_KEYS):
                self._notify_manual_restart_required("settings changes")

    def _hotkey_signature(self, config: IniConfigLoader) -> tuple[str | bool, ...]:
        advanced_options = config.advanced_options
        return (
            advanced_options.run_vision_mode,
            advanced_options.exit_key,
            advanced_options.info_overlay,
            advanced_options.toggle_paragon_overlay,
            advanced_options.vision_mode_only,
            advanced_options.run_filter,
            advanced_options.run_filter_drop,
            advanced_options.run_filter_force_refresh,
            advanced_options.force_refresh_only,
            advanced_options.move_to_inv,
            advanced_options.move_to_chest,
        )

    def _refresh_hotkeys(self, config: IniConfigLoader) -> None:
        if sys.platform == "darwin":
            return

        current_signature = self._hotkey_signature(config)
        if getattr(self, "_current_hotkey_signature", None) == current_signature:
            return

        self._clear_key_binds()
        self.setup_key_binds()
        LOGGER.info("Reloaded hotkeys from updated settings")

    def _refresh_language_assets(self, config: IniConfigLoader) -> None:
        if config.general.language == self._language:
            return

        Dataloader().load_data()
        self._language = config.general.language
        LOGGER.info("Reloaded language assets for %s", self._language)

    def _refresh_logging_level(self, config: IniConfigLoader) -> None:
        current_log_level = config.advanced_options.log_lvl.value.upper()
        if current_log_level == self._log_level:
            return

        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler.setLevel(current_log_level)
        self._log_level = current_log_level
        LOGGER.info("Updated log level to %s", current_log_level)

    def _notify_manual_restart_required(self, reason: str) -> None:
        if self._manual_restart_warning:
            return

        self._manual_restart_warning = True
        LOGGER.warning("Please restart d4lf manually to apply %s.", reason)

    def toggle_paragon_overlay(self):
        """Toggle the Paragon overlay thread (start if not running, request close if running)."""
        try:
            if self.paragon_overlay_thread is not None and self.paragon_overlay_thread.is_alive():
                LOGGER.info("Closing Paragon overlay")
                with suppress(Exception):
                    request_close()
                self.paragon_overlay_thread.join(timeout=2)
                # Vision mode is restored by the overlay thread cleanup.
                return

            config = self._config
            overlay_dir = config.user_dir / "profiles"
            overlay_dir.mkdir(parents=True, exist_ok=True)

            yaml_files = list(overlay_dir.glob("*.yaml")) + list(overlay_dir.glob("*.yml"))
            if not yaml_files:
                LOGGER.warning(
                    "No profile YAML files found in %s. Import a build first (Importer), then open the overlay again.",
                    overlay_dir,
                )

            # Disable vision mode while the overlay is active; restore it when the overlay closes.
            self._vision_mode_was_running_before_overlay = self.vision_mode.running()
            if self._vision_mode_was_running_before_overlay:
                self.vision_mode.stop()

            LOGGER.info("Opening Paragon overlay (source: %s)", overlay_dir)
            self.paragon_overlay_thread = threading.Thread(
                target=self._run_paragon_overlay, args=(str(overlay_dir),), daemon=True
            )
            self.paragon_overlay_thread.start()

        except Exception:
            LOGGER.exception("Failed to toggle Paragon overlay")

    def _run_paragon_overlay(self, preset_path: str) -> None:
        try:
            run_paragon_overlay(preset_path)
        except Exception:
            LOGGER.exception("Paragon overlay crashed")
        finally:
            try:
                if self._vision_mode_was_running_before_overlay and not self.vision_mode.running():
                    self.vision_mode.start()
            except Exception:
                LOGGER.exception("Failed to restore vision mode after Paragon overlay")
            finally:
                self.paragon_overlay_thread = None

    def toggle_info_overlay(self):
        """Toggle the Info Panel overlay."""
        if LOCK.acquire(blocking=False):
            try:
                now = time.time()
                # Debounce to prevent rapid key-repeat triggers
                if now - self._last_info_overlay_toggle < 1.5:
                    return
                self._last_info_overlay_toggle = now

                if self.info_overlay_thread is not None and self.info_overlay_thread.is_alive():
                    from src.info_overlay import request_close
                    LOGGER.info("Closing Info Panel overlay")
                    request_close()
                    self.info_overlay_thread.join(timeout=2.0)
                    if not self.info_overlay_thread.is_alive():
                        self.info_overlay_thread = None
                else:
                    from src.info_overlay import run_boss_timer_overlay
                    LOGGER.info("Opening Info Panel overlay")
                    self.info_overlay_thread = threading.Thread(target=run_boss_timer_overlay, daemon=True)
                    self.info_overlay_thread.start()
                    # Ensure the thread is registered as alive before the lock is released
                    time.sleep(0.1)
            except Exception:
                LOGGER.exception("Failed to toggle Info Panel overlay")
            finally:
                LOCK.release()

    def _clear_key_binds(self) -> None:
        if sys.platform == "darwin":
            return

        while self._hotkey_handles:
            handle = self._hotkey_handles.pop()
            with suppress(KeyError, ValueError):
                keyboard.remove_hotkey(handle)

    def _register_hotkey(self, hotkey: str, callback: Callable[[], None]) -> None:
        self._hotkey_handles.append(keyboard.add_hotkey(hotkey, callback))

    def setup_key_binds(self):
        if sys.platform == "darwin":
            LOGGER.info("Global hotkeys are disabled on macOS")
            return

        config = self._config
        advanced_options = config.advanced_options
        self._register_hotkey(advanced_options.run_vision_mode, lambda: self.run_vision_mode())
        self._register_hotkey(advanced_options.exit_key, lambda: self._graceful_exit())
        self._register_hotkey(advanced_options.toggle_paragon_overlay, lambda: self.toggle_paragon_overlay())
        self._register_hotkey(advanced_options.info_overlay, lambda: self.toggle_info_overlay())
        self._register_hotkey(config.char.inventory, lambda: InventoryExpTracker().on_inventory_open())
        if not advanced_options.vision_mode_only:
            self._register_hotkey(advanced_options.run_filter, lambda: self.filter_items())
            self._register_hotkey(advanced_options.run_filter_drop, lambda: self.filter_items(no_match_action="drop"))
            self._register_hotkey(
                advanced_options.run_filter_force_refresh, lambda: self.filter_items(ItemRefreshType.force_with_filter)
            )
            self._register_hotkey(
                advanced_options.force_refresh_only, lambda: self.filter_items(ItemRefreshType.force_without_filter)
            )
            self._register_hotkey(advanced_options.move_to_inv, lambda: self.move_items_to_inventory())
            self._register_hotkey(advanced_options.move_to_chest, lambda: self.move_items_to_stash())

        self._current_hotkey_signature = self._hotkey_signature(config)

    def filter_items(self, force_refresh=ItemRefreshType.no_refresh, no_match_action: str = "junk"):
        if src.tts.CONNECTED:
            self._start_or_stop_loot_interaction_thread(run_loot_filter, (force_refresh, no_match_action))
        else:
            LOGGER.warning(
                "TTS connection has not been made yet. Have you followed all of the instructions in %s? "
                "If so, it's possible your Windows user does not have the correct permissions to allow Diablo 4 "
                "to connect to a third party screen reader.",
                SETUP_INSTRUCTIONS_URL,
            )

    def move_items_to_inventory(self):
        self._start_or_stop_loot_interaction_thread(move_items_to_inventory)

    def move_items_to_stash(self):
        self._start_or_stop_loot_interaction_thread(move_items_to_stash)

    def _start_or_stop_loot_interaction_thread(self, loot_interaction_method: Callable[..., None], method_args=()):
        if LOCK.acquire(blocking=False):
            try:
                if self.loot_interaction_thread is not None:
                    LOGGER.info("Stopping filter or move process")
                    kill_thread(self.loot_interaction_thread)
                    self.loot_interaction_thread = None
                    if self.did_stop_scripts and not self.vision_mode.running():
                        self.vision_mode.start()
                else:
                    self.loot_interaction_thread = threading.Thread(
                        target=self._wrapper_run_loot_interaction_method,
                        args=(loot_interaction_method, method_args),
                        daemon=True,
                    )
                    self.loot_interaction_thread.start()
            finally:
                LOCK.release()
        else:
            return

    def _wrapper_run_loot_interaction_method(self, loot_interaction_method: Callable[..., None], method_args=()):
        try:
            # We will stop all scripts if they are currently running and restart them afterward if needed.
            self.did_stop_scripts = False
            if self.vision_mode.running():
                self.vision_mode.stop()
                self.did_stop_scripts = True

            loot_interaction_method(*method_args)

            if self.did_stop_scripts:
                self.run_vision_mode()
        finally:
            self.loot_interaction_thread = None

    def run_vision_mode(self):
        if LOCK.acquire(blocking=False):
            try:
                if self.vision_mode.running():
                    self.vision_mode.stop()
                else:
                    self.vision_mode.start()
            finally:
                LOCK.release()
        else:
            return

def _hover_experience_balance():
    # Experience bar is approximately centered at the very bottom of the window
    from src.info_overlay import load_info_settings
    info_config = load_info_settings()
    if info_config["exp_bar_pos"]:
        if len(info_config["exp_bar_pos"]) == 4:
            x1, y1, x2, y2 = info_config["exp_bar_pos"]
            mouse.move(*Cam().window_to_monitor((x1, y1)))
            time.sleep(0.1)
            mouse.move(*Cam().window_to_monitor((x2, y2)))
        else:
            mouse.move(*Cam().window_to_monitor(info_config["exp_bar_pos"]))
    else:
        win_roi = Cam().window_roi
        exp_pos = (int(win_roi["width"] * 0.5), int(win_roi["height"] * 0.965))
        mouse.move(*Cam().window_to_monitor(exp_pos))
    time.sleep(0.5)


def run_loot_filter(force_refresh: ItemRefreshType = ItemRefreshType.no_refresh, no_match_action: str = "junk"):
    LOGGER.info("Running loot filter")
    mouse.move(*Cam().abs_window_to_monitor((0, 0)))
    check_items = src.scripts.loot_filter_tts.check_items

    inv = CharInventory()
    stash = Stash()
    config = IniConfigLoader()

    if stash.is_open():
        for i in config.general.check_chest_tabs:
            stash.switch_to_tab(i)
            time.sleep(0.3)
            check_items(stash, force_refresh, stash_is_open=True, no_match_action="junk")
        mouse.move(*Cam().abs_window_to_monitor((0, 0)))
        time.sleep(0.3)
        check_items(inv, force_refresh, stash_is_open=True, no_match_action="junk")
        _hover_experience_balance()
    else:
        if not inv.open():
            screenshot("inventory_not_open", img=Cam().grab())
            LOGGER.error("Inventory did not open up")
            return
        check_items(inv, force_refresh, no_match_action=no_match_action)
        _hover_experience_balance()
    mouse.move(*Cam().abs_window_to_monitor((0, 0)))
    LOGGER.info("Loot filter done")
