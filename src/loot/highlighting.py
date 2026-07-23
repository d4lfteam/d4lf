"""Highlighting vision mode orchestration and lifecycle."""

import logging
import queue
from typing import TYPE_CHECKING, Literal

import numpy as np

from src.automation import character_inventory, stash_inventory, vendor_inventory
from src.desktop import call_on_ui_thread, create_overlay_toplevel, get_root
from src.item import FilterResult
from src.loot.highlighting_render import HighlightingRenderer
from src.loot.highlighting_worker import HighlightingWorker
from src.loot.singleton import singleton
from src.perception import Publisher, capture, game_window_roi
from src.settings import get_ui_coordinates

if TYPE_CHECKING:
    import tkinter as tk
    from threading import Event, Thread

    from src.item import Item

LOGGER = logging.getLogger(__name__)

type HighlightTask = (
    tuple[Literal["clear"]]
    | tuple[Literal["empty"], Item, tuple[int, int, int, int], str, str | None]
    | tuple[Literal["match"], Item, tuple[int, int, int, int], FilterResult, object | None]
    | tuple[Literal["no_match"], Item, tuple[int, int, int, int]]
    | tuple[Literal["codex_upgrade"], Item, tuple[int, int, int, int], FilterResult]
)


@singleton
class VisionModeWithHighlighting(HighlightingRenderer, HighlightingWorker):
    def __init__(self):
        super().__init__()
        self.root: tk.Toplevel
        self.canvas: tk.Canvas
        self.clear_when_item_not_selected_thread: Thread | None = None
        self.clear_when_item_not_selected_thread_cancel_event: Event | None = None
        self.evaluate_item_thread: Thread | None = None
        self.evaluate_item_thread_cancel_event: Event | None = None
        self.current_item: Item | None = None
        self.is_cleared: bool = True
        self.queue: queue.Queue[HighlightTask] = queue.Queue()
        self.is_running: bool = False

        def _build_ui() -> None:
            self.root, self.canvas = create_overlay_toplevel(get_root())
            self.root.geometry("0x0+0+0")
            self.draw_from_queue()

        # Widget creation and every subsequent Tk call must happen on the
        # shared UI thread, not whichever thread constructs this singleton.
        call_on_ui_thread(_build_ui)

        self.thick = int(game_window_roi()["height"] * 0.0047)

        inv = character_inventory()
        stash = stash_inventory()
        vendor = vendor_inventory()
        img = capture()
        self.max_slot_size = stash.get_max_slot_size()
        occ_inv, empty_inv = inv.get_item_slots(img)
        occ_stash, empty_stash = stash.get_item_slots(img)
        occ_vendor, empty_vendor = vendor.get_item_slots(img)
        possible_centers = []
        possible_centers += [slot.center for slot in occ_inv]
        possible_centers += [slot.center for slot in empty_inv]

        # add possible centers of equipped items
        for x in get_ui_coordinates().pos.possible_centers:
            possible_centers.append(x)

        possible_vendor_centers = possible_centers.copy()
        possible_vendor_centers += [slot.center for slot in occ_vendor]
        possible_vendor_centers += [slot.center for slot in empty_vendor]

        possible_centers += [slot.center for slot in occ_stash]
        possible_centers += [slot.center for slot in empty_stash]

        self.possible_centers = np.array(possible_centers)
        self.possible_vendor_centers = np.array(possible_vendor_centers)

        window_roi = game_window_roi()
        self.screen_off_x = window_roi["left"]
        self.screen_off_y = window_roi["top"]

    def request_clear(self):
        self.queue.put(("clear",))

    def request_empty_outline(self, item_descr, item_roi, color, text: str | None = None):
        self.queue.put(("empty", item_descr, item_roi, color, text))

    def request_match_box(self, item_descr, item_roi, should_keep_res, locator_result):
        self.queue.put(("match", item_descr, item_roi, should_keep_res, locator_result))

    def request_no_match_box(self, item_descr, item_roi):
        self.queue.put(("no_match", item_descr, item_roi))

    def request_codex_upgrade_box(self, item_descr, item_roi, res):
        self.queue.put(("codex_upgrade", item_descr, item_roi, res))

    def start(self):
        LOGGER.info("Starting Vision Mode")
        Publisher().subscribe_item(self.on_tts)
        self.is_running = True

    def stop(self):
        LOGGER.info("Stopping Vision Mode")
        self.request_clear()
        if self.evaluate_item_thread:
            self.stop_thread_and_wait(self.evaluate_item_thread, self.evaluate_item_thread_cancel_event)
            self.evaluate_item_thread = None
        if self.clear_when_item_not_selected_thread:
            self.stop_thread_and_wait(
                self.clear_when_item_not_selected_thread, self.clear_when_item_not_selected_thread_cancel_event
            )
            self.clear_when_item_not_selected_thread = None
        Publisher().unsubscribe_item(self.on_tts)
        self.is_running = False

    def running(self):
        return self.is_running
