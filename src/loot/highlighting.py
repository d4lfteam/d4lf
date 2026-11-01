"""Highlighting vision mode orchestration and lifecycle."""

import logging

import numpy as np

from src.automation import character_inventory, stash_inventory, vendor_inventory
from src.loot.highlighting_render import HighlightingOverlay
from src.loot.highlighting_worker import HighlightingWorker
from src.loot.singleton import singleton
from src.perception import Publisher, capture, game_window_roi
from src.settings import get_ui_coordinates

LOGGER = logging.getLogger(__name__)


class HighlightingVisionMode:
    """Highlights hovered items by evaluating them in a worker and drawing the result on an overlay."""

    def __init__(self) -> None:
        self.is_running = False
        window_roi = game_window_roi()
        self.overlay = HighlightingOverlay.create(
            int(window_roi["height"] * 0.0047), (window_roi["left"], window_roi["top"])
        )

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

        self.worker = HighlightingWorker(self.overlay, np.array(possible_centers), np.array(possible_vendor_centers))

    def start(self) -> None:
        LOGGER.info("Starting Vision Mode")
        Publisher().subscribe_item(self.worker.on_tts)
        self.is_running = True

    def stop(self) -> None:
        LOGGER.info("Stopping Vision Mode")
        self.overlay.clear()
        self.worker.stop()
        Publisher().unsubscribe_item(self.worker.on_tts)
        self.is_running = False

    def running(self) -> bool:
        return self.is_running


VisionModeWithHighlighting = singleton(HighlightingVisionMode)
