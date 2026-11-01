import time
import typing
from threading import Event, Thread
from types import SimpleNamespace
from typing import override

import numpy as np
import pytest

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

import src.loot.highlighting.worker as worker_module
import src.perception
from src.game_data import ItemRarity, ItemType
from src.item import FilterResult, Item, MatchedFilter
from src.loot.highlighting.overlay import ClearCommand, HighlightingVisionMode, OverlayCommand
from src.loot.highlighting.pipeline import MatchCommand
from src.loot.highlighting.worker import (
    CancellationRequestedError,
    HighlightingWorker,
    check_for_thread_cancellation,
    stop_thread_and_wait,
)

CENTERS = np.array([[0, 0]])


class _RecordingOverlay(HighlightingVisionMode):
    """Overlay without Tk that records what it would draw."""

    def __init__(self, item: Item | None, mocker: MockerFixture) -> None:
        super().__init__(mocker.Mock(), mocker.Mock(), 4, (0, 0), CENTERS, CENTERS)
        self.current_item = item
        self.drawn: list[OverlayCommand] = []

    @override
    def draw(self, command: OverlayCommand) -> None:
        self.drawn.append(command)
        if isinstance(command, ClearCommand):
            command.done.set()

    def drain(self) -> None:
        for _ in range(10):
            self.draw_from_queue()

    def drain_later(self, delay_seconds: float) -> None:
        """Stand-in for Tk that starts processing the queue after a delay."""

        def drain() -> None:
            time.sleep(delay_seconds)
            for _ in range(100):
                self.draw_from_queue()
                time.sleep(0.01)

        Thread(target=drain, daemon=True).start()


def test_cancellation_check_raises_for_set_event() -> None:
    event = Event()
    event.set()
    with pytest.raises(CancellationRequestedError):
        check_for_thread_cancellation(event)


def test_unparsed_tts_keeps_existing_item_overlay(monkeypatch, mocker: MockerFixture) -> None:
    item = Item(name="gohrs_devastating_grips")
    overlay = _RecordingOverlay(item, mocker)
    monkeypatch.setattr(worker_module, "capture", mocker.Mock())
    monkeypatch.setattr(src.perception, "read_latest_item", lambda: None)

    HighlightingWorker(overlay, CENTERS, CENTERS).on_tts([])
    overlay.drain()

    assert overlay.current_item is item
    assert overlay.drawn == []


@pytest.mark.parametrize(
    ("filter_result", "should_queue_match"),
    [(FilterResult(False, [], skipped=True), False), (FilterResult(True, [MatchedFilter("Mythic Sigil")]), True)],
)
def test_filter_result_submits_only_normal_highlighting_results(
    monkeypatch, filter_result, should_queue_match, mocker: MockerFixture
) -> None:
    item = Item(name="helm", item_type=ItemType.Sigil, rarity=ItemRarity.Mythic if should_queue_match else None)
    overlay = _RecordingOverlay(item, mocker)
    cleared = Event()
    cleared.set()
    monkeypatch.setattr(overlay, "clear", lambda: cleared)

    detection = SimpleNamespace(found=True, cropped_descr=object(), crop_roi=(0, 0, 10, 10))
    monkeypatch.setattr(worker_module, "pointer_position", lambda: (0, 0))
    monkeypatch.setattr(worker_module, "monitor_to_window", lambda position: position)
    monkeypatch.setattr(worker_module, "capture", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(worker_module, "find_descr_with_diagnostics", lambda *_args: detection)
    monkeypatch.setattr(worker_module, "find_descr", lambda *_args: (True, object(), None))
    monkeypatch.setattr(worker_module, "compare_histograms", lambda *_args: 1.0)
    monkeypatch.setattr(worker_module, "is_ignored_item", lambda _item: False)
    monkeypatch.setattr(worker_module, "Filter", lambda: SimpleNamespace(should_keep=lambda _item: filter_result))
    monkeypatch.setattr(worker_module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        worker_module.threading, "Thread", lambda *_args, **_kwargs: SimpleNamespace(start=lambda: None)
    )

    checks = 0

    def stop_after_first_evaluation(_event: Event) -> None:
        nonlocal checks
        checks += 1
        if checks > 5:
            raise CancellationRequestedError

    monkeypatch.setattr(worker_module, "check_for_thread_cancellation", stop_after_first_evaluation)

    HighlightingWorker(overlay, CENTERS, CENTERS).evaluate_item_and_queue_draw(item, Event())
    overlay.drain()

    assert [type(command) for command in overlay.drawn] == ([MatchCommand] if should_queue_match else [])


def _stop_at_detection(monkeypatch, overlay: _RecordingOverlay) -> list[list[str]]:
    drawn_at_detection: list[list[str]] = []
    monkeypatch.setattr(worker_module, "pointer_position", lambda: (0, 0))
    monkeypatch.setattr(worker_module, "monitor_to_window", lambda position: position)
    monkeypatch.setattr(worker_module, "capture", lambda *_args, **_kwargs: object())

    def find_descr_stub(*_args):
        drawn_at_detection.append([type(command).__name__ for command in overlay.drawn])
        raise CancellationRequestedError

    monkeypatch.setattr(worker_module, "find_descr_with_diagnostics", find_descr_stub)
    return drawn_at_detection


def test_detection_waits_for_own_clear_behind_pending_match_draw(monkeypatch, mocker: MockerFixture) -> None:
    item = Item(name="helm")
    overlay = _RecordingOverlay(item, mocker)
    # Draw submitted by the previous thread that Tk has not consumed yet.
    overlay.submit(MatchCommand(item, (0, 0, 10, 10), FilterResult(True, []), None))
    drawn_at_detection = _stop_at_detection(monkeypatch, overlay)
    worker = HighlightingWorker(overlay, CENTERS, CENTERS)

    thread = Thread(target=worker.evaluate_item_and_queue_draw, args=(item, Event()), daemon=True)
    thread.start()
    overlay.drain_later(0.2)
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert drawn_at_detection == [["MatchCommand", "ClearCommand"]]


def test_cancellation_ends_thread_waiting_for_clear(monkeypatch, mocker: MockerFixture) -> None:
    item = Item(name="helm")
    overlay = _RecordingOverlay(item, mocker)  # nothing ever consumes the queued clear
    drawn_at_detection = _stop_at_detection(monkeypatch, overlay)
    worker = HighlightingWorker(overlay, CENTERS, CENTERS)
    cancel_event = Event()

    thread = Thread(target=worker.evaluate_item_and_queue_draw, args=(item, cancel_event), daemon=True)
    thread.start()
    thread.join(timeout=0.3)
    assert thread.is_alive()  # stuck waiting for the clear

    stopper = Thread(target=stop_thread_and_wait, args=(thread, cancel_event), daemon=True)
    stopper.start()
    stopper.join(timeout=1)

    assert not stopper.is_alive()
    assert not thread.is_alive()
    assert drawn_at_detection == []
