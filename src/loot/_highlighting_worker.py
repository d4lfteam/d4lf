"""Tooltip evaluation and cancellation for highlighting mode."""

import logging
import threading
import time
from threading import Event, Thread
from typing import TYPE_CHECKING, Any

import numpy as np

import src.perception
from src.automation import pointer_position
from src.item import ASPECT_UPGRADES_LABEL, Filter, SeasonalAttribute, is_sigil
from src.perception import (
    LocatorResult,
    capture,
    compare_image_histograms,
    find_descr,
    find_descr_with_diagnostics,
    get_separator_match_in_crop,
    locate_affix_markers,
    monitor_to_window,
    screenshot,
)

from ._colors import get_filter_colors, is_ignored_item

if TYPE_CHECKING:
    from src.item import Item

LOGGER = logging.getLogger(__name__)
_FRAME_RETRY_DELAY_SECONDS = 0.01


class CancellationRequestedError(Exception):
    """Exception raised when a cancellation is requested."""


class HighlightingWorker:
    def on_tts(self: Any, _):
        img = capture()
        item_descr = None
        try:
            item_descr = src.perception.read_latest_item()
            LOGGER.debug(f"Parsed item based on TTS: {item_descr}")
        except Exception:
            screenshot("tts_error", img=img)
            LOGGER.exception(f"Error in TTS read_descr. {src.perception.latest_item_lines()=}")

        if item_descr is None:
            self.request_clear()
            return

        self.current_item = item_descr

        # Kick off a thread that will evaluate the item and queue up the appropriate drawings.
        # If one already exists we'll kill it since a new item has come in
        if self.evaluate_item_thread:
            self.stop_thread_and_wait(self.evaluate_item_thread, self.evaluate_item_thread_cancel_event)

        cancel_event = threading.Event()
        self.evaluate_item_thread_cancel_event = cancel_event
        self.evaluate_item_thread = threading.Thread(
            target=self.evaluate_item_and_queue_draw, args=(item_descr, cancel_event), daemon=True
        )
        self.evaluate_item_thread.start()

    def evaluate_item_and_queue_draw(self: Any, item_descr: Item, cancel_event: Event) -> None:
        if not self.is_cleared:
            self.request_clear()
        if self.clear_when_item_not_selected_thread:
            self.stop_thread_and_wait(
                self.clear_when_item_not_selected_thread, self.clear_when_item_not_selected_thread_cancel_event
            )
            self.clear_when_item_not_selected_thread = None

        last_top_left_corner = None
        last_center = None
        # Each item must be detected twice and the image must match, this is to avoid
        # getting in item while the fade-in animation and failing to read it properly
        is_confirmed = False
        retry_count = 0
        try:
            while retry_count < 5 and not is_confirmed:
                self.check_for_thread_cancellation(cancel_event)
                retry_count += 1
                mouse_pos = monitor_to_window(pointer_position())
                # get closest pos to a item center
                centers_to_use = self.possible_vendor_centers if item_descr.is_in_shop else self.possible_centers
                delta = centers_to_use - mouse_pos
                distances = np.linalg.norm(delta, axis=1)
                closest_index = np.argmin(distances)
                item_center_array = centers_to_use[closest_index]
                item_center = (int(item_center_array[0]), int(item_center_array[1]))

                self.check_for_thread_cancellation(cancel_event)
                # Before we get the cropped_descr we need to ensure there is no previous overlay on screen
                while not self.is_cleared:
                    time.sleep(0.10)
                detection = find_descr_with_diagnostics(capture(), item_center)
                found = detection.found
                cropped_descr = detection.cropped_descr
                item_roi = detection.crop_roi

                top_left_corner = None if not found or item_roi is None else item_roi[:2]
                if found and item_roi is not None:
                    if not is_confirmed:
                        time.sleep(_FRAME_RETRY_DELAY_SECONDS)
                        self.check_for_thread_cancellation(cancel_event)
                        found_check, cropped_descr_check, _ = find_descr(capture(), item_center)
                        if not found_check:
                            continue
                        score = compare_image_histograms(cropped_descr, cropped_descr_check)
                        if score < 0.99:
                            continue
                        is_confirmed = True

                    self.check_for_thread_cancellation(cancel_event)

                    moved_to_new_item = (
                        last_top_left_corner is None
                        or top_left_corner is None
                        or last_top_left_corner != top_left_corner
                        or (last_center is not None and last_center[1] != item_center[1])
                    )
                    if moved_to_new_item:
                        ignored_item = is_ignored_item(item_descr)
                        # Make the canvas blue for ignored items. Other items wait for the final result.
                        if ignored_item:
                            if item_descr.seasonal_attribute == SeasonalAttribute.sanctified:
                                self.request_empty_outline(
                                    item_descr, item_roi, get_filter_colors().unhandled, "Sanctified (Not Supported)"
                                )
                            else:
                                self.request_empty_outline(item_descr, item_roi, get_filter_colors().unhandled)

                        # Remove any final drawing if the item is unselected. It is also automatically
                        # removed if a different TTS item comes in.
                        self.check_for_thread_cancellation(cancel_event)
                        # Since we've now drawn something we kick off a thread to remove the drawing
                        # if the item is unselected. It is also automatically removed if a different
                        # TTS item comes in.
                        if not self.clear_when_item_not_selected_thread:
                            clear_cancel_event = threading.Event()
                            self.clear_when_item_not_selected_thread_cancel_event = clear_cancel_event
                            self.clear_when_item_not_selected_thread = threading.Thread(
                                target=self.check_for_item_still_selected,
                                args=(item_center, clear_cancel_event),
                                daemon=True,
                            )
                            self.clear_when_item_not_selected_thread.start()

                        if ignored_item:
                            return

                        # Check if the item is a match based on our filters
                        last_top_left_corner = top_left_corner
                        last_center = item_center

                        if item_descr == self.current_item:
                            res = Filter().should_keep(item_descr)
                            match = res.keep

                            # Adapt colors based on config
                            if match:
                                locator_result = None
                                if any(
                                    res_matched.profile.endswith(ASPECT_UPGRADES_LABEL) for res_matched in res.matched
                                ):
                                    self.request_codex_upgrade_box(item_descr, item_roi, res)
                                else:
                                    if not is_sigil(item_descr.item_type):
                                        matched_affixes = res.matched[0].matched_affixes if res.matched else []
                                        aspect_matched = any(m.aspect_match for m in res.matched)

                                        def locate_markers(
                                            tooltip_image: np.ndarray,
                                            *,
                                            item=item_descr,
                                            matched_affixes=matched_affixes,
                                            aspect_matched=aspect_matched,
                                            short_separator_match=None,
                                        ) -> LocatorResult:
                                            return locate_affix_markers(
                                                tooltip_image=tooltip_image,
                                                item=item,
                                                matched_affixes=matched_affixes,
                                                aspect_matched=aspect_matched,
                                                short_separator_match=short_separator_match,
                                            )

                                        def locate_markers_for_detection(detection) -> LocatorResult:
                                            return locate_markers(
                                                detection.cropped_descr,
                                                short_separator_match=get_separator_match_in_crop(detection),
                                            )

                                        locator_result = locate_markers_for_detection(detection)
                                        if not locator_result.reliable:
                                            # Bullet templates may still be fading after the tooltip is confirmed.
                                            time.sleep(_FRAME_RETRY_DELAY_SECONDS)
                                            self.check_for_thread_cancellation(cancel_event)
                                            retry_detection = find_descr_with_diagnostics(capture(), item_center)
                                            if retry_detection.found:
                                                locator_result = locate_markers_for_detection(retry_detection)
                                                item_roi = retry_detection.crop_roi
                                    self.request_match_box(item_descr, item_roi, res, locator_result)
                            elif not match:
                                self.request_no_match_box(item_descr, item_roi)
                else:
                    self.request_clear()
                    self.check_for_thread_cancellation(cancel_event)
                    last_center = None
                    last_top_left_corner = None
                    is_confirmed = False
                    time.sleep(0.15)
        except CancellationRequestedError:
            pass
        except Exception:
            LOGGER.exception(
                "Error in vision mode. If an item was mid-transition this is harmless; if it repeats, please create a bug report."
            )
        finally:
            self.evaluate_item_thread = None

    @staticmethod
    def check_for_thread_cancellation(cancel_event: Event):
        if cancel_event.is_set():
            raise CancellationRequestedError

    @staticmethod
    def stop_thread_and_wait(thread: Thread | None, cancel_event: Event | None) -> None:
        if thread is None or cancel_event is None:
            return
        cancel_event.set()
        thread.join()

    def check_for_item_still_selected(self: Any, item_center: tuple[int, int], cancel_event: Event) -> None:
        try:
            while True:
                self.check_for_thread_cancellation(cancel_event)
                found_check, _, _ = find_descr(capture(), item_center)
                if not found_check:
                    self.request_clear()
                    self.clear_when_item_not_selected_thread = None
                    break
                time.sleep(0.15)
        except CancellationRequestedError:
            self.clear_when_item_not_selected_thread = None
