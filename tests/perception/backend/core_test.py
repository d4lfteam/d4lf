import sys

from src.perception.backend.core import load_backend
from src.perception.backend.noop import NoopTTSBackend


def test_backend_loader_uses_the_noop_adapter_outside_windows() -> None:
    backend = load_backend()
    if sys.platform != "win32":
        assert isinstance(backend, NoopTTSBackend)
