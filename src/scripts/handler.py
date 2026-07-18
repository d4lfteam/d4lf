import logging
import threading
import time
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Set as AbstractSet

import src.perception
from src import automation
from src.automation import (
    WindowSpec,
    is_window_foreground,
    kill_thread,
    move_items_to_inventory,
    move_items_to_stash,
    safe_exit,
)
from src.dataloader import Dataloader
from src.loot import VisionMode, create_vision_mode, run_loot_filter
from src.paragon import request_close as request_close_paragon
from src.paragon import run_paragon_overlay
from src.scripts.info_overlay import InventoryExpTracker, is_info_overlay_open, open_boss_timer_overlay, request_close
from src.scripts.info_overlay import set_busy_checker as set_info_busy_checker
from src.settings import (
    HOTKEY_SETTING_KEYS,
    LANGUAGE_SETTING_KEYS,
    MANUAL_RESTART_SETTING_KEYS,
    VISION_MODE_TYPE_SETTING_KEY,
    ItemRefreshType,
    Settings,
    VisionModeType,
    get_settings,
    has_any_changed,
)

LOGGER = logging.getLogger(__name__)
LOCK = threading.Lock()
SETUP_INSTRUCTIONS_URL = "https://github.com/d4lfteam/d4lf/blob/main/README.md#how-to-setup"


class ScriptHandler:
    def __init__(self):
        self.loot_interaction_thread: threading.Thread | None = None
        self.paragon_overlay_thread: threading.Thread | None = None
        self._info_overlay_last_toggle_time: float = 0
        self.did_stop_scripts: bool = False
        self._vision_mode_was_running_before_overlay: bool = False
        self._hotkey_handles: list[int] = []
        self._runtime_config_lock = threading.RLock()
        self._manual_restart_warning: bool = False
        self._config = get_settings()
        self._win_spec = WindowSpec(self._config.advanced_options.process_name)
        self._language = self._config.general.language
        self.vision_mode: VisionMode = self._create_vision_mode(self._config.general.vision_mode_type)

        # Initialize Info Overlay hooks and subscriptions
        set_info_busy_checker(lambda: self.loot_interaction_thread is not None)

        self.setup_key_binds()
        self._config.register_change_listener(self._on_config_changed)
        if self._config.general.run_vision_mode_on_startup:
            self.run_vision_mode()

    def _create_vision_mode(self, vision_mode_type: VisionModeType) -> VisionMode:
        return create_vision_mode(vision_mode_type)

    def _graceful_exit(self):
        safe_exit()

    def _on_config_changed(self, changed_keys: AbstractSet[str]) -> None:
        """Apply relevant settings after a config change event."""
        with self._runtime_config_lock:
            if has_any_changed(changed_keys, HOTKEY_SETTING_KEYS):
                self._refresh_hotkeys(self._config)
            if has_any_changed(changed_keys, LANGUAGE_SETTING_KEYS):
                self._refresh_language_assets(self._config)
            if VISION_MODE_TYPE_SETTING_KEY in changed_keys:
                self._notify_manual_restart_required("vision mode changes")
            elif has_any_changed(changed_keys, MANUAL_RESTART_SETTING_KEYS):
                self._notify_manual_restart_required("settings changes")

    def _hotkey_signature(self, config: Settings) -> tuple[str | bool, ...]:
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

    def _refresh_hotkeys(self, config: Settings) -> None:
        current_signature = self._hotkey_signature(config)
        if getattr(self, "_current_hotkey_signature", None) == current_signature:
            return

        self._clear_key_binds()
        self.setup_key_binds()
        LOGGER.info("Reloaded hotkeys from updated settings")

    def _refresh_language_assets(self, config: Settings) -> None:
        if config.general.language == self._language:
            return

        Dataloader().load_data()
        self._language = config.general.language
        LOGGER.info("Reloaded language assets for %s", self._language)

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
                    request_close_paragon()
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
        """Toggle the Info Panel overlay (debounced; show/hide a widget on the shared UI thread)."""
        now = time.time()
        # Debounce to prevent rapid key-repeat triggers
        if now - self._info_overlay_last_toggle_time < 0.3:
            return
        self._info_overlay_last_toggle_time = now

        if is_info_overlay_open():
            LOGGER.info("Closing Info Panel overlay")
            with suppress(Exception):
                request_close()
            return

        LOGGER.info("Opening Info Panel overlay")
        try:
            open_boss_timer_overlay()
        except Exception:
            LOGGER.exception("Info Panel overlay crashed")

    def _clear_key_binds(self) -> None:
        while self._hotkey_handles:
            handle = self._hotkey_handles.pop()
            with suppress(KeyError, ValueError):
                automation.remove_hotkey(handle)

    def _register_hotkey(self, hotkey: str, callback: Callable[[], None], check_focus: bool = True) -> None:
        def wrapped_callback():
            if not check_focus or is_window_foreground(self._win_spec):
                callback()

        self._hotkey_handles.append(automation.add_hotkey(hotkey, wrapped_callback))

    def setup_key_binds(self):
        config = self._config
        advanced_options = config.advanced_options
        self._register_hotkey(advanced_options.run_vision_mode, lambda: self.run_vision_mode())
        self._register_hotkey(advanced_options.exit_key, lambda: self._graceful_exit(), check_focus=False)
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
        if src.perception.is_connected():
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
