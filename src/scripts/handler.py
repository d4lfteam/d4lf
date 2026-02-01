import logging
import sys
import threading
import time
import typing
import subprocess
from contextlib import suppress
from pathlib import Path

if sys.platform != "darwin":
    import keyboard
import src.scripts.loot_filter_tts
import src.scripts.vision_mode_fast
import src.scripts.vision_mode_with_highlighting
import src.tts
from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import ItemRefreshType, VisionModeType
from src.loot_mover import move_items_to_inventory, move_items_to_stash
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
        self.paragon_overlay_proc = None
        self._paragon_overlay_log = None
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
        """Toggle the Paragon overlay process (start if not running, stop if running)."""
        try:
            # If already running -> stop it
            if self.paragon_overlay_proc is not None and self.paragon_overlay_proc.poll() is None:
                LOGGER.info("Closing Paragon overlay")
                with suppress(Exception):
                    self.paragon_overlay_proc.terminate()
                with suppress(Exception):
                    self.paragon_overlay_proc.wait(timeout=2)
                self.paragon_overlay_proc = None
                with suppress(Exception):
                    if self._paragon_overlay_log is not None:
                        self._paragon_overlay_log.close()
                self._paragon_overlay_log = None
                return

            config = IniConfigLoader()
            overlay_dir_str = getattr(config.advanced_options, "paragon_overlay_source_dir", "") or ""
            overlay_dir = Path(overlay_dir_str).expanduser() if str(overlay_dir_str).strip() else (config.user_dir / "paragon")
            overlay_dir.mkdir(parents=True, exist_ok=True)

            json_files = list(Path(overlay_dir).glob("*.json"))
            if not json_files:
                LOGGER.warning(
                    f"No Paragon JSON files found in {overlay_dir}. Import a build first or place *.json files there."
                )

            # Build command to launch overlay mode
            if getattr(sys, "frozen", False):
                cmd = [sys.executable, "--paragon-overlay", str(overlay_dir)]
                cwd = str(Path(sys.executable).parent)
            else:
                # From source: ensure project root is cwd so `-m src.main` works reliably
                project_root = Path(__file__).resolve().parents[2]
                cmd = [sys.executable, "-m", "src.main", "--paragon-overlay", str(overlay_dir)]
                cwd = str(project_root)

            creationflags = 0
            startupinfo = None
            if sys.platform == "win32":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                except Exception:
                    startupinfo = None

            LOGGER.info(f"Opening Paragon overlay (source: {overlay_dir})")
            # Capture any overlay errors in a log file (important when console is hidden)
            log_path = overlay_dir / "paragon_overlay.log"
            try:
                self._paragon_overlay_log = open(log_path, "a", encoding="utf-8", errors="ignore")
            except Exception:
                self._paragon_overlay_log = None

            self.paragon_overlay_proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=self._paragon_overlay_log or subprocess.DEVNULL,
                stderr=self._paragon_overlay_log or subprocess.DEVNULL,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )

            # If it exits immediately, surface the issue in the D4LF log.
            time.sleep(0.2)
            if self.paragon_overlay_proc.poll() is not None:
                LOGGER.error(
                    "Paragon overlay exited immediately (code=%s). See log: %s",
                    self.paragon_overlay_proc.returncode,
                    log_path,
                )

        except Exception:
            LOGGER.exception("Failed to toggle Paragon overlay")

    def setup_key_binds(self):
        keyboard.add_hotkey(IniConfigLoader().advanced_options.run_vision_mode, lambda: self.run_vision_mode())
        keyboard.add_hotkey(IniConfigLoader().advanced_options.exit_key, lambda: self._graceful_exit())
        keyboard.add_hotkey(IniConfigLoader().advanced_options.toggle_paragon_overlay, lambda: self.toggle_paragon_overlay())
        if not IniConfigLoader().advanced_options.vision_mode_only:
            keyboard.add_hotkey(IniConfigLoader().advanced_options.run_filter, lambda: self.filter_items())
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

    def filter_items(self, force_refresh=ItemRefreshType.no_refresh):
        if src.tts.CONNECTED:
            self._start_or_stop_loot_interaction_thread(run_loot_filter, (force_refresh,))
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


def run_loot_filter(force_refresh: ItemRefreshType = ItemRefreshType.no_refresh):
    LOGGER.info("Running loot filter")
    mouse.move(*Cam().abs_window_to_monitor((0, 0)))
    check_items = src.scripts.loot_filter_tts.check_items

    inv = CharInventory()
    stash = Stash()

    if stash.is_open():
        for i in IniConfigLoader().general.check_chest_tabs:
            stash.switch_to_tab(i)
            time.sleep(0.3)
            check_items(stash, force_refresh, stash_is_open=True)
        mouse.move(*Cam().abs_window_to_monitor((0, 0)))
        time.sleep(0.3)
        check_items(inv, force_refresh, stash_is_open=True)
    else:
        if not inv.open():
            screenshot("inventory_not_open", img=Cam().grab())
            LOGGER.error("Inventory did not open up")
            return
        check_items(inv, force_refresh)
    mouse.move(*Cam().abs_window_to_monitor((0, 0)))
    LOGGER.info("Loot Filter done")
