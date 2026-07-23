import pytest

from src.perception.backend.noop import NoopTTSBackend


def test_noop_backend_rejects_named_pipe_creation() -> None:
    with pytest.raises(RuntimeError, match="only supported on Windows"):
        NoopTTSBackend().create_pipe(None)


def test_noop_backend_does_not_start_threads() -> None:
    backend = NoopTTSBackend()
    backend.read_pipe(None, None, None, lambda _connected: None)
    backend.start_connection(None, None, None)
