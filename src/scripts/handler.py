import logging
import sys
import threading
import time
import typing
from contextlib import suppress

if sys.platform != "darwin":
    import keyboard  # type: ignore[import-not-found]
else:
    keyboard = None

import src.scripts.loot_filter_tts
import src.scripts.vision_mode_fast
import src.scripts.vision_mode_with_highlighting
import src.tts
from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import ItemRefreshType, VisionModeType
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


class ScriptHandler:
    def __init__(self):
        self.loot_interaction_thread = None
        self.paragon_overlay_thread: threading.Thread | None = None
        self._vision_mode_was_running_before_overlay = False
        if IniConfigLoader().general.vision_mode_type == VisionModeType.fast:
            self.vision_mode = src.scripts.vision_mode_fast.VisionModeFast()
        else:
            self.vision_mode = src.scripts.vision_mode_with_highlighting.VisionModeWithHighlighting()

        self.setup_key_binds()
        if IniConfigLoader().general.run_vision_mode_on_startup:
            self.run_vision_mode()

    def _graceful_exit(self):
        safe_exit()

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

            config = IniConfigLoader()
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
            # Overlay has stopped (or failed to start). Restore vision mode if we stopped it.
            try:
                if self._vision_mode_was_running_before_overlay and not self.vision_mode.running():
                    self.vision_mode.start()
            except Exception:
                LOGGER.exception("Failed to restore vision mode after Paragon overlay")
            finally:
                self.paragon_overlay_thread = None

    def setup_key_binds(self):
        if keyboard is None:
            LOGGER.info("Global hotkeys are disabled on macOS")
            return
        keyboard.add_hotkey(IniConfigLoader().advanced_options.run_vision_mode, lambda: self.run_vision_mode())
        keyboard.add_hotkey(IniConfigLoader().advanced_options.exit_key, lambda: self._graceful_exit())
        keyboard.add_hotkey(
            IniConfigLoader().advanced_options.toggle_paragon_overlay, lambda: self.toggle_paragon_overlay()
        )
        if not IniConfigLoader().advanced_options.vision_mode_only:
            keyboard.add_hotkey(IniConfigLoader().advanced_options.run_filter, lambda: self.filter_items())
            keyboard.add_hotkey(
                IniConfigLoader().advanced_options.run_filter_drop, lambda: self.filter_items(no_match_action="drop")
            )
            keyboard.add_hotkey(
                IniConfigLoader().advanced_options.run_filter_force_refresh,
                lambda: self.filter_items(ItemRefreshType.force_with_filter),
            )
            keyboard.add_hotkey(
                IniConfigLoader().advanced_options.force_refresh_only,
                lambda: self.filter_items(ItemRefreshType.force_without_filter),
            )
            keyboard.add_hotkey(IniConfigLoader().advanced_options.move_to_inv, lambda: self.move_items_to_inventory())
            keyboard.add_hotkey(IniConfigLoader().advanced_options.move_to_chest, lambda: self.move_items_to_stash())

    def filter_items(self, force_refresh=ItemRefreshType.no_refresh, no_match_action: str = "junk"):
        if src.tts.CONNECTED:
            self._start_or_stop_loot_interaction_thread(run_loot_filter, (force_refresh, no_match_action))
        else:
            LOGGER.warning(
                f"TTS connection has not been made yet. Have you followed all of the instructions in {SETUP_INSTRUCTIONS_URL}? "
                f"If so, it's possible your Windows user does not have the correct permissions to allow Diablo 4 to connect to a third party screen reader."
            )

    def move_items_to_inventory(self):
        self._start_or_stop_loot_interaction_thread(move_items_to_inventory)

    def move_items_to_stash(self):
        self._start_or_stop_loot_interaction_thread(move_items_to_stash)

    def _start_or_stop_loot_interaction_thread(self, loot_interaction_method: typing.Callable, method_args=()):
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

    def _wrapper_run_loot_interaction_method(self, loot_interaction_method: typing.Callable, method_args=()):
        try:
            # We will stop all scripts if they are currently running and restart them afterward if needed
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
