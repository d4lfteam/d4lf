from __future__ import annotations

import logging
import sys
import threading
import time
from contextlib import suppress
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Set as AbstractSet

if sys.platform != "darwin":
    try:
        import keyboard
    except Exception:  # pragma: no cover
        keyboard = None  # type: ignore[assignment]
else:
    keyboard = None  # type: ignore[assignment]

import src.scripts.loot_filter_tts
import src.scripts.vision_mode_fast
import src.scripts.vision_mode_with_highlighting
import src.tts
from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import (
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
from src.scripts.hotkeys import (
    HOTKEY_SETTING_KEYS,
    LANGUAGE_SETTING_KEYS,
    LOG_LEVEL_SETTING_KEYS,
    MANUAL_RESTART_SETTING_KEYS,
    VISION_MODE_TYPE_SETTING_KEY,
    build_hotkey_signature,
    has_any_changed,
)
from src.scripts.runtime_lifecycle import (
    refresh_language_assets,
    refresh_logging_level,
    should_notify_manual_restart,
)
from src.ui.char_inventory import CharInventory
from src.ui.stash import Stash
from src.utils.custom_mouse import mouse
from src.utils.process_handler import kill_thread, safe_exit
from src.utils.window import screenshot

LOGGER = logging.getLogger(__name__)

LOCK = threading.Lock()


class ScriptHandler:
    def __init__(self):
        self.loot_interaction_thread = None
        self.paragon_overlay_thread: threading.Thread | None = None
        self.did_stop_scripts = False
        self._vision_mode_was_running_before_overlay = False
        self._hotkey_handles: list[Any] = []
        self._runtime_config_lock = threading.RLock()
        self._manual_restart_warning = False
        self._config = IniConfigLoader()
        self._language = self._config.general.language
        self._log_level = self._config.advanced_options.log_lvl.value.upper()
        self.vision_mode = self._create_vision_mode(self._config.general.vision_mode_type)

        self.setup_key_binds()
        self._config.register_change_listener(self._on_config_changed)
        if self._config.general.run_vision_mode_on_startup:
            self.run_vision_mode()

    def _create_vision_mode(self, vision_mode_type: VisionModeType):
        if vision_mode_type == VisionModeType.fast:
            return src.scripts.vision_mode_fast.VisionModeFast()
        return src.scripts.vision_mode_with_highlighting.VisionModeWithHighlighting()

    def _graceful_exit(self):
        safe_exit()

    def _on_config_changed(self, changed_keys: AbstractSet[str]) -> None:
        """Apply relevant settings after a config change event."""
        with self._runtime_config_lock:
            if has_any_changed(changed_keys, LOG_LEVEL_SETTING_KEYS):
                self._refresh_logging_level(self._config)
            if has_any_changed(changed_keys, HOTKEY_SETTING_KEYS):
                self._refresh_hotkeys(self._config)
            if has_any_changed(changed_keys, LANGUAGE_SETTING_KEYS):
                self._refresh_language_assets(self._config)
            if VISION_MODE_TYPE_SETTING_KEY in changed_keys:
                self._notify_manual_restart_required("vision mode changes")
            elif has_any_changed(changed_keys, MANUAL_RESTART_SETTING_KEYS):
                self._notify_manual_restart_required("settings changes")

    def _hotkey_signature(self, config: IniConfigLoader) -> tuple[str | bool, ...]:
        return build_hotkey_signature(config.advanced_options)

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
        updated_language = refresh_language_assets(self._language, config.general.language, Dataloader())
        if updated_language == self._language:
            return
        self._language = updated_language
        LOGGER.info("Reloaded language assets for %s", self._language)

    def _refresh_logging_level(self, config: IniConfigLoader) -> None:
        current_log_level = config.advanced_options.log_lvl.value.upper()
        updated_log_level = refresh_logging_level(self._log_level, current_log_level, logging.getLogger())
        if updated_log_level == self._log_level:
            return
        self._log_level = updated_log_level
        LOGGER.info("Updated log level to %s", current_log_level)

    def _notify_manual_restart_required(self, reason: str) -> None:
        if not should_notify_manual_restart(self._manual_restart_warning):
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

    def _clear_key_binds(self) -> None:
        if sys.platform == "darwin" or keyboard is None:
            return

        while self._hotkey_handles:
            handle = self._hotkey_handles.pop()
            with suppress(KeyError, ValueError):
                keyboard.remove_hotkey(handle)

    def _register_hotkey(self, hotkey: str, callback: Callable[[], None]) -> None:
        if keyboard is None:
            return
        self._hotkey_handles.append(keyboard.add_hotkey(hotkey, callback))

    def setup_key_binds(self):
        if sys.platform == "darwin" or keyboard is None:
            LOGGER.info("Global hotkeys are disabled on macOS")
            return

        config = self._config
        advanced_options = config.advanced_options
        self._register_hotkey(advanced_options.run_vision_mode, lambda: self.run_vision_mode())
        self._register_hotkey(advanced_options.exit_key, lambda: self._graceful_exit())
        self._register_hotkey(advanced_options.toggle_paragon_overlay, lambda: self.toggle_paragon_overlay())
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


def run_loot_filter(force_refresh: ItemRefreshType = ItemRefreshType.no_refresh, no_match_action: str = "junk"):
    LOGGER.info("Running loot filter")
    mouse.move(*Cam().abs_window_to_monitor((0, 0)))
    check_items = src.scripts.loot_filter_tts.check_items

    inv = CharInventory()
    stash = Stash()

    if stash.is_open():
        for i in IniConfigLoader().general.check_chest_tabs:
            stash.switch_to_tab(i)
            time.sleep(0.3)
            check_items(stash, force_refresh, stash_is_open=True, no_match_action="junk")
        mouse.move(*Cam().abs_window_to_monitor((0, 0)))
        time.sleep(0.3)
        check_items(inv, force_refresh, stash_is_open=True, no_match_action="junk")
    else:
        if not inv.open():
            screenshot("inventory_not_open", img=Cam().grab())
            LOGGER.error("Inventory did not open up")
            return
        check_items(inv, force_refresh, no_match_action=no_match_action)
    mouse.move(*Cam().abs_window_to_monitor((0, 0)))
    LOGGER.info("Loot filter done")
