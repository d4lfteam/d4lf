from threading import Event

import pytest

from src.loot._highlighting_worker import CancellationRequestedError, HighlightingWorker


def test_cancellation_error_is_public_within_worker_module():
    assert issubclass(CancellationRequestedError, Exception)


def test_cancellation_check_raises_for_set_event():
    event = Event()
    event.set()
    with pytest.raises(CancellationRequestedError):
        HighlightingWorker.check_for_thread_cancellation(event)
