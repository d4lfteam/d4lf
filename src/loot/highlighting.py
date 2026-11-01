"""Highlighting vision mode creation."""

import numpy as np

from src.automation import character_inventory, stash_inventory, vendor_inventory
from src.loot.highlighting_render import HighlightingVisionMode
from src.loot.vision_mode import create_on_ui_thread
from src.perception import capture, game_window_roi
from src.settings import get_ui_coordinates


def create_highlighting_vision_mode() -> HighlightingVisionMode:
    window_roi = game_window_roi()
    thick = int(window_roi["height"] * 0.0047)
    screen_offset = (window_roi["left"], window_roi["top"])

    inv = character_inventory()
    stash = stash_inventory()
    vendor = vendor_inventory()
    img = capture()
    occ_inv, empty_inv = inv.get_item_slots(img)
    occ_stash, empty_stash = stash.get_item_slots(img)
    occ_vendor, empty_vendor = vendor.get_item_slots(img)
    # inventory and equipped item centers are possible everywhere
    possible_centers = [slot.center for slot in occ_inv + empty_inv]
    possible_centers += get_ui_coordinates().pos.possible_centers
    possible_vendor_centers = possible_centers + [slot.center for slot in occ_vendor + empty_vendor]
    possible_centers += [slot.center for slot in occ_stash + empty_stash]

    return create_on_ui_thread(
        lambda root, canvas: HighlightingVisionMode(
            root, canvas, thick, screen_offset, np.array(possible_centers), np.array(possible_vendor_centers)
        )
    )
