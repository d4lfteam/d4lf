import typing
from threading import Event, Thread
from types import SimpleNamespace
from typing import cast

import pytest

if typing.TYPE_CHECKING:
    from unittest.mock import Mock

    import numpy as np
    from pytest_mock import MockerFixture

    from src.loot.highlighting import VisionModeWithHighlighting
    from src.perception import LocatorResult

import src.loot.highlighting_worker as worker_module
import src.perception
from src.game_data import ItemRarity, ItemType
from src.item import FilterResult, Item, MatchedFilter
from src.loot.highlighting_worker import CancellationRequestedError, HighlightingWorker


class _WorkerHarness(HighlightingWorker):
    current_item: Item | None
    is_cleared: bool
    clear_when_item_not_selected_thread: Thread | None
    clear_when_item_not_selected_thread_cancel_event: Event | None
    possible_centers: np.ndarray
    possible_vendor_centers: np.ndarray
    request_clear_mock: Mock
    request_match_box_mock: Mock
    request_no_match_box_mock: Mock
    request_empty_outline_mock: Mock
    request_codex_upgrade_box_mock: Mock

    def request_clear(self) -> None:
        self.request_clear_mock()

    def request_match_box(
        self, *args: Item | FilterResult | tuple[int, int, int, int] | LocatorResult | str | None
    ) -> None:
        self.request_match_box_mock(*args)

    def request_no_match_box(self, *args: Item | tuple[int, int, int, int]) -> None:
        self.request_no_match_box_mock(*args)

    def request_empty_outline(self, *args: Item | tuple[int, int, int, int] | str | None) -> None:
        self.request_empty_outline_mock(*args)

    def request_codex_upgrade_box(self, *args: Item | FilterResult | tuple[int, int, int, int]) -> None:
        self.request_codex_upgrade_box_mock(*args)


def test_cancellation_error_is_public_within_worker_module() -> None:
    assert issubclass(CancellationRequestedError, Exception)


def test_cancellation_check_raises_for_set_event() -> None:
    event = Event()
    event.set()
    with pytest.raises(CancellationRequestedError):
        HighlightingWorker.check_for_thread_cancellation(event)


def test_unparsed_tts_does_not_clear_existing_item_overlay(monkeypatch, mocker: MockerFixture) -> None:
    worker = _WorkerHarness()
    worker.current_item = Item(name="gohrs_devastating_grips")
    worker.request_clear_mock = mocker.Mock()

    monkeypatch.setattr("src.loot.highlighting_worker.capture", mocker.Mock())
    monkeypatch.setattr(src.perception, "read_latest_item", lambda: None)

    cast("VisionModeWithHighlighting", worker).on_tts([])

    worker.request_clear_mock.assert_not_called()


@pytest.mark.parametrize(
    ("filter_result", "should_queue_match"),
    [(FilterResult(False, [], skipped=True), False), (FilterResult(True, [MatchedFilter("Mythic Sigil")]), True)],
)
def test_filter_result_queues_only_normal_highlighting_results(
    monkeypatch, mocker: MockerFixture, filter_result, should_queue_match
) -> None:
    worker = _WorkerHarness()
    item = Item(name="helm", item_type=ItemType.Sigil, rarity=ItemRarity.Mythic if should_queue_match else None)
    worker.current_item = item
    worker.is_cleared = True
    worker.clear_when_item_not_selected_thread = None
    worker.clear_when_item_not_selected_thread_cancel_event = None
    worker.request_clear_mock = mocker.Mock()
    worker.request_match_box_mock = mocker.Mock()
    worker.request_no_match_box_mock = mocker.Mock()
    worker.request_empty_outline_mock = mocker.Mock()
    worker.request_codex_upgrade_box_mock = mocker.Mock()
    worker.possible_centers = worker_module.np.array([[0, 0]])
    worker.possible_vendor_centers = worker.possible_centers

    detection = SimpleNamespace(found=True, cropped_descr=object(), crop_roi=(0, 0, 10, 10))
    monkeypatch.setattr(worker_module, "pointer_position", lambda: (0, 0))
    monkeypatch.setattr(worker_module, "monitor_to_window", lambda position: position)
    monkeypatch.setattr("src.loot.highlighting_worker.capture", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(worker_module, "find_descr_with_diagnostics", lambda *_args: detection)
    monkeypatch.setattr(worker_module, "find_descr", lambda *_args: (True, object(), None))
    monkeypatch.setattr(worker_module, "compare_histograms", lambda *_args: 1.0)
    monkeypatch.setattr(worker_module, "is_ignored_item", lambda _item: False)
    monkeypatch.setattr(worker_module, "Filter", lambda: SimpleNamespace(should_keep=lambda _item: filter_result))
    monkeypatch.setattr(worker_module.time, "sleep", lambda _seconds: None)

    def fake_thread(*_args, **_kwargs):
        return SimpleNamespace(start=lambda: None)

    monkeypatch.setattr(worker_module.threading, "Thread", fake_thread)

    checks = 0

    def stop_after_first_evaluation(_worker, _event) -> None:
        nonlocal checks
        checks += 1
        if checks > 5:
            raise CancellationRequestedError

    monkeypatch.setattr(HighlightingWorker, "check_for_thread_cancellation", stop_after_first_evaluation)

    cast("VisionModeWithHighlighting", worker).evaluate_item_and_queue_draw(item, Event())

    if should_queue_match:
        worker.request_match_box_mock.assert_called_once()
    else:
        worker.request_match_box_mock.assert_not_called()
    worker.request_no_match_box_mock.assert_not_called()
    worker.request_empty_outline_mock.assert_not_called()
    worker.request_codex_upgrade_box_mock.assert_not_called()
