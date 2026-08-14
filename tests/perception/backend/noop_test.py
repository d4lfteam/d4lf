import logging
import queue

import pytest

from src.perception.backend.noop import NoopTTSBackend


def test_noop_backend_rejects_named_pipe_creation() -> None:
    with pytest.raises(RuntimeError, match="only supported on Windows"):
        NoopTTSBackend().create_pipe(logging.getLogger(__name__))


def test_noop_backend_does_not_start_threads() -> None:
    backend = NoopTTSBackend()
    backend.read_pipe(lambda: 1, queue.Queue(), logging.getLogger(__name__), lambda _connected: None)
    backend.start_connection(lambda: None, lambda: None, logging.getLogger(__name__))
