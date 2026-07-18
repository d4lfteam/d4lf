"""Loot interaction orchestration shared by the application handler."""

import logging
import time

from src.automation import character_inventory, move_pointer, stash_inventory
from src.perception import abs_window_to_monitor, capture, screenshot
from src.settings import ItemRefreshType, get_settings

from ._filter import check_items

LOGGER = logging.getLogger(__name__)


def run_loot_filter(force_refresh: ItemRefreshType = ItemRefreshType.no_refresh, no_match_action: str = "junk"):
    LOGGER.info("Running loot filter")
    move_pointer(*abs_window_to_monitor((0, 0)))
    inv = character_inventory()
    stash = stash_inventory()

    if stash.is_open():
        for tab in get_settings().general.check_chest_tabs:
            stash.switch_to_tab(tab)
            time.sleep(0.3)
            check_items(stash, force_refresh, stash_is_open=True, no_match_action="junk")
        move_pointer(*abs_window_to_monitor((0, 0)))
        time.sleep(0.3)
        check_items(inv, force_refresh, stash_is_open=True, no_match_action="junk")
    else:
        if not inv.open():
            screenshot("inventory_not_open", img=capture())
            LOGGER.error("Inventory did not open up")
            return
        check_items(inv, force_refresh, no_match_action=no_match_action)
    move_pointer(*abs_window_to_monitor((0, 0)))
    LOGGER.info("Loot filter done")
