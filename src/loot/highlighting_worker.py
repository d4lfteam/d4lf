"""Tooltip evaluation and cancellation for highlighting mode."""

import logging
import threading
import time
from threading import Event, Thread
from typing import TYPE_CHECKING

import src.perception
from src.automation import pointer_position
from src.game_data import is_sigil
from src.item import SeasonalAttribute
from src.item.filter import Filter
from src.loot.colors import get_filter_colors, is_ignored_item
from src.loot.highlighting_pipeline import (
    CodexUpgradeCommand,
    EmptyOutlineCommand,
    FilterOutcome,
    MatchCommand,
    NoMatchCommand,
    RenderingCommand,
    TooltipConfirmationStatus,
    classify_filter_outcome,
    confirm_stable_tooltip,
    locate_markers_with_retry,
    select_rendering_command,
    select_target_center,
)
from src.perception import (
    LocatorResult,
    capture,
    compare_histograms,
    find_descr,
    find_descr_with_diagnostics,
    get_separator_match_in_crop,
    locate_affix_markers,
    monitor_to_window,
    screenshot,
)

if TYPE_CHECKING:
    from src.item import Affix, Item
    from src.loot.highlighting import VisionModeWithHighlighting
    from src.perception import DescrDetection

LOGGER = logging.getLogger(__name__)
_FRAME_RETRY_DELAY_SECONDS = 0.01


class CancellationRequestedError(Exception):
    """Exception raised when a cancellation is requested."""


class HighlightingWorker:
    def on_tts(self: VisionModeWithHighlighting, _: list[str]) -> None:
        img = capture()
        item_descr = None
        try:
            item_descr = src.perception.read_latest_item()
            LOGGER.debug(f"Parsed item based on TTS: {item_descr}")
        except Exception:
            screenshot("tts_error", img=img)
            LOGGER.exception(f"Error in TTS read_descr. {src.perception.latest_item_lines()=}")

        if item_descr is None:
            # Diablo can emit a transient second TTS event for the same tooltip. The
            # screen watcher is responsible for clearing an overlay when the tooltip
            # actually disappears, so an unparseable event must not erase valid markers.
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

    def evaluate_item_and_queue_draw(self: VisionModeWithHighlighting, item_descr: Item, cancel_event: Event) -> None:
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
                item_center = select_target_center(
                    monitor_to_window(pointer_position()),
                    self.possible_centers,
                    self.possible_vendor_centers,
                    is_in_shop=item_descr.is_in_shop,
                ).center

                self.check_for_thread_cancellation(cancel_event)
                # Before we get the cropped_descr we need to ensure there is no previous overlay on screen
                while not self.is_cleared:
                    time.sleep(0.10)
                detection = find_descr_with_diagnostics(capture(), item_center)
                confirmation = confirm_stable_tooltip(detection, already_confirmed=is_confirmed)
                if confirmation.status is TooltipConfirmationStatus.ABSENT:
                    self.request_clear()
                    self.check_for_thread_cancellation(cancel_event)
                    last_center = None
                    last_top_left_corner = None
                    time.sleep(0.15)
                    is_confirmed = False
                    continue
                if confirmation.status is TooltipConfirmationStatus.INVALID:
                    continue

                if not is_confirmed:
                    time.sleep(_FRAME_RETRY_DELAY_SECONDS)
                    self.check_for_thread_cancellation(cancel_event)
                    found_check, cropped_descr_check, _ = find_descr(capture(force_new=True), item_center)
                    score = (
                        compare_histograms(detection.cropped_descr, cropped_descr_check)
                        if found_check and cropped_descr_check is not None and detection.cropped_descr is not None
                        else None
                    )
                    confirmation = confirm_stable_tooltip(
                        detection,
                        already_confirmed=False,
                        second_found=found_check,
                        second_cropped_descr=cropped_descr_check,
                        histogram_score=score,
                    )
                    if not confirmation.confirmed:
                        continue
                    is_confirmed = True

                self.check_for_thread_cancellation(cancel_event)

                item_roi_tuple = confirmation.item_roi
                top_left_corner = confirmation.top_left_corner
                if item_roi_tuple is None or top_left_corner is None:
                    continue
                moved_to_new_item = (
                    last_top_left_corner is None
                    or last_top_left_corner != top_left_corner
                    or (last_center is not None and last_center[1] != item_center[1])
                )
                if moved_to_new_item:
                    ignored_item = is_ignored_item(item_descr)
                    # Make the canvas blue for ignored items. Other items wait for the final result.
                    if ignored_item:
                        command = select_rendering_command(
                            item_descr,
                            item_roi_tuple,
                            ignored_item=True,
                            ignored_color=get_filter_colors().unhandled,
                            sanctified=item_descr.seasonal_attribute == SeasonalAttribute.sanctified,
                            filter_evaluation=None,
                        )
                        if command is not None:
                            self._queue_rendering_command(command)

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
                        evaluation = classify_filter_outcome(
                            item_descr, self.current_item, Filter().should_keep(item_descr)
                        )
                        if evaluation.outcome is FilterOutcome.SKIPPED:
                            return

                        locator_result = None
                        if evaluation.outcome is FilterOutcome.MATCH and not is_sigil(item_descr.item_type):
                            marker_affixes: list[Affix] = list(evaluation.matched_affixes)
                            marker_aspect_matched = evaluation.aspect_matched

                            def locate_markers_for_detection(
                                detection: DescrDetection,
                                *,
                                matched_affixes: list[Affix] = marker_affixes,
                                aspect_matched: bool = marker_aspect_matched,
                            ) -> LocatorResult:
                                if detection.cropped_descr is None:
                                    return LocatorResult(markers=[], reliable=False)
                                return locate_affix_markers(
                                    tooltip_image=detection.cropped_descr,
                                    item=item_descr,
                                    matched_affixes=matched_affixes,
                                    aspect_matched=aspect_matched,
                                    short_separator_match=get_separator_match_in_crop(detection),
                                )

                            marker_location = locate_markers_with_retry(detection, locate=locate_markers_for_detection)
                            locator_result = marker_location.locator_result
                            if not locator_result.reliable:
                                # Bullet templates may still be fading after the tooltip is confirmed.
                                time.sleep(_FRAME_RETRY_DELAY_SECONDS)
                                self.check_for_thread_cancellation(cancel_event)
                                retry_detection = find_descr_with_diagnostics(capture(), item_center)
                                marker_location = locate_markers_with_retry(
                                    detection,
                                    locate=locate_markers_for_detection,
                                    retry_detection=retry_detection if retry_detection.found else None,
                                    initial_result=locator_result,
                                )
                                locator_result = marker_location.locator_result
                                if marker_location.item_roi is not None:
                                    item_roi_tuple = marker_location.item_roi

                        command = select_rendering_command(
                            item_descr,
                            item_roi_tuple,
                            ignored_item=False,
                            sanctified=False,
                            filter_evaluation=evaluation,
                            locator_result=locator_result,
                        )
                        if command is not None:
                            self._queue_rendering_command(command)
        except CancellationRequestedError:
            pass
        except Exception:
            LOGGER.exception(
                "Error in vision mode. If an item was mid-transition this is harmless; if it repeats, please create a bug report."
            )
        finally:
            self.evaluate_item_thread = None

    def _queue_rendering_command(self: VisionModeWithHighlighting, command: RenderingCommand) -> None:
        if isinstance(command, EmptyOutlineCommand):
            if command.text is None:
                self.request_empty_outline(command.item, command.item_roi, command.color)
            else:
                self.request_empty_outline(command.item, command.item_roi, command.color, command.text)
        elif isinstance(command, MatchCommand):
            self.request_match_box(command.item, command.item_roi, command.filter_result, command.locator_result)
        elif isinstance(command, NoMatchCommand):
            self.request_no_match_box(command.item, command.item_roi)
        elif isinstance(command, CodexUpgradeCommand):
            self.request_codex_upgrade_box(command.item, command.item_roi, command.filter_result)

    @staticmethod
    def check_for_thread_cancellation(cancel_event: Event) -> None:
        if cancel_event.is_set():
            raise CancellationRequestedError

    @staticmethod
    def stop_thread_and_wait(thread: Thread | None, cancel_event: Event | None) -> None:
        if thread is None or cancel_event is None:
            return
        cancel_event.set()
        thread.join()

    def check_for_item_still_selected(
        self: VisionModeWithHighlighting, item_center: tuple[int, int], cancel_event: Event
    ) -> None:
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
