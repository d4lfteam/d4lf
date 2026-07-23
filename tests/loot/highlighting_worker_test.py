import typing
from threading import Event
from types import SimpleNamespace

import pytest

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

import src.loot.highlighting_worker as worker_module
import src.perception
from src.item import FilterResult, Item, ItemRarity, ItemType, MatchedFilter
from src.loot.highlighting_worker import CancellationRequestedError, HighlightingWorker


def test_cancellation_error_is_public_within_worker_module():
    assert issubclass(CancellationRequestedError, Exception)


def test_cancellation_check_raises_for_set_event():
    event = Event()
    event.set()
    with pytest.raises(CancellationRequestedError):
        HighlightingWorker.check_for_thread_cancellation(event)


def test_unparsed_tts_does_not_clear_existing_item_overlay(monkeypatch, mocker: MockerFixture):
    worker = object.__new__(HighlightingWorker)
    worker.current_item = Item(name="gohrs_devastating_grips")
    worker.request_clear = mocker.Mock()

    monkeypatch.setattr("src.loot.highlighting_worker.capture", mocker.Mock())
    monkeypatch.setattr(src.perception, "read_latest_item", lambda: None)

    worker.on_tts([])

    worker.request_clear.assert_not_called()


@pytest.mark.parametrize(
    ("filter_result", "should_queue_match"),
    [(FilterResult(False, [], skipped=True), False), (FilterResult(True, [MatchedFilter("Mythic Sigil")]), True)],
)
def test_filter_result_queues_only_normal_highlighting_results(
    monkeypatch, mocker: MockerFixture, filter_result, should_queue_match
):
    worker = object.__new__(HighlightingWorker)
    item = Item(name="helm", item_type=ItemType.Sigil, rarity=ItemRarity.Mythic if should_queue_match else None)
    worker.current_item = item
    worker.is_cleared = True
    worker.clear_when_item_not_selected_thread = None
    worker.clear_when_item_not_selected_thread_cancel_event = None
    worker.request_clear = mocker.Mock()
    worker.request_match_box = mocker.Mock()
    worker.request_no_match_box = mocker.Mock()
    worker.request_empty_outline = mocker.Mock()
    worker.request_codex_upgrade_box = mocker.Mock()
    worker.possible_centers = worker_module.np.array([[0, 0]])
    worker.possible_vendor_centers = worker.possible_centers

    detection = SimpleNamespace(found=True, cropped_descr=object(), crop_roi=(0, 0, 10, 10))
    monkeypatch.setattr(worker_module, "pointer_position", lambda: (0, 0))
    monkeypatch.setattr(worker_module, "monitor_to_window", lambda position: position)
    monkeypatch.setattr("src.loot.highlighting_worker.capture", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(worker_module, "find_descr_with_diagnostics", lambda *_args: detection)
    monkeypatch.setattr(worker_module, "find_descr", lambda *_args: (True, object(), None))
    monkeypatch.setattr(worker_module, "compare_image_histograms", lambda *_args: 1.0)
    monkeypatch.setattr(worker_module, "is_ignored_item", lambda _item: False)
    monkeypatch.setattr(worker_module, "Filter", lambda: SimpleNamespace(should_keep=lambda _item: filter_result))
    monkeypatch.setattr(worker_module.time, "sleep", lambda _seconds: None)

    def fake_thread(*_args, **_kwargs):
        return SimpleNamespace(start=lambda: None)

    monkeypatch.setattr(worker_module.threading, "Thread", fake_thread)

    checks = 0

    def stop_after_first_evaluation(_worker, _event):
        nonlocal checks
        checks += 1
        if checks > 5:
            raise CancellationRequestedError

    monkeypatch.setattr(HighlightingWorker, "check_for_thread_cancellation", stop_after_first_evaluation)

    worker.evaluate_item_and_queue_draw(item, Event())

    if should_queue_match:
        worker.request_match_box.assert_called_once()
    else:
        worker.request_match_box.assert_not_called()
    worker.request_no_match_box.assert_not_called()
    worker.request_empty_outline.assert_not_called()
    worker.request_codex_upgrade_box.assert_not_called()
