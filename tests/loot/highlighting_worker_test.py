import typing
from threading import Event

import pytest

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

import src.perception
from src.item import Item
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
