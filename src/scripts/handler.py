import logging
import threading
import time
import typing

import keyboard

import src.item.descr.read_descr_tts
import src.logger
import src.scripts.loot_filter
import src.scripts.loot_filter_tts
import src.scripts.vision_mode
import src.scripts.vision_mode_mixed
import src.scripts.vision_mode_tts
import src.tts
from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import ItemRefreshType, UseTTSType
from src.loot_mover import move_items_to_inventory, move_items_to_stash
from src.scripts.common import SETUP_INSTRUCTIONS_URL
from src.ui.char_inventory import CharInventory
from src.ui.chest import Chest
from src.utils.custom_mouse import mouse
from src.utils.process_handler import kill_thread, safe_exit
from src.utils.window import screenshot

LOGGER = logging.getLogger(__name__)

LOCK = threading.Lock()


class ScriptHandler:
    def __init__(self):
        self.loot_interaction_thread = None
        if IniConfigLoader().general.use_tts == UseTTSType.full:
            self.vision_mode = src.scripts.vision_mode_tts.VisionModeTTS()
        else:
            self.vision_mode = src.scripts.vision_mode_mixed.VisionModeMixed()

        self.setup_key_binds()
        if IniConfigLoader().general.run_vision_mode_on_startup:
            self.run_scripts()

    def setup_key_binds(self):
        keyboard.add_hotkey(IniConfigLoader().advanced_options.run_scripts, lambda: self.run_scripts())
        keyboard.add_hotkey(IniConfigLoader().advanced_options.exit_key, lambda: safe_exit())
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
        if IniConfigLoader().general.use_tts in [UseTTSType.full, UseTTSType.mixed]:
            if src.tts.CONNECTED:
                self._start_or_stop_loot_interaction_thread(run_loot_filter, (force_refresh, True))
            else:
                LOGGER.warning(
                    f"TTS connection has not been made yet. Have you followed all of the instructions in {SETUP_INSTRUCTIONS_URL}? "
                    f"If so, it's possible your Windows user does not have the correct permissions to allow Diablo 4 to connect to a third party screen reader."
                )
        else:
            self._start_or_stop_loot_interaction_thread(run_loot_filter, (force_refresh, False))

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
                        target=self._wrapper_run_loot_interaction_method, args=(loot_interaction_method, method_args), daemon=True
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
                self.run_scripts()
        finally:
            self.loot_interaction_thread = None

    def run_scripts(self):
        if LOCK.acquire(blocking=False):
            try:
                if not IniConfigLoader().advanced_options.scripts:
                    LOGGER.info("No scripts configured")
                    return

                # TODO Probably just remove the "scripts" concept and change to a checkbox for vision mode
                if self.vision_mode.running():
                    self.vision_mode.stop()
                else:
                    self.vision_mode.start()
            finally:
                LOCK.release()
        else:
            return


def run_loot_filter(force_refresh: ItemRefreshType = ItemRefreshType.no_refresh, tts: bool = False):
    LOGGER.info("Running loot filter")
    mouse.move(*Cam().abs_window_to_monitor((0, 0)))
    check_items = src.scripts.loot_filter_tts.check_items if tts else src.scripts.loot_filter.check_items

    inv = CharInventory()
    chest = Chest()

    if chest.is_open():
        for i in IniConfigLoader().general.check_chest_tabs:
            chest.switch_to_tab(i)
            time.sleep(0.3)
            check_items(chest, force_refresh)
        mouse.move(*Cam().abs_window_to_monitor((0, 0)))
        time.sleep(0.3)
        check_items(inv, force_refresh)
    else:
        if not inv.open():
            screenshot("inventory_not_open", img=Cam().grab())
            LOGGER.error("Inventory did not open up")
            return
        check_items(inv, force_refresh)
    mouse.move(*Cam().abs_window_to_monitor((0, 0)))
    LOGGER.info("Loot Filter done")
