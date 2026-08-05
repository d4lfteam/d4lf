import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows named-pipe adapter")

if sys.platform == "win32":
    from src.perception.backend.windows import WindowsTTSBackend


def test_windows_backend_module_is_only_exercised_on_windows() -> None:
    assert WindowsTTSBackend.__name__ == "WindowsTTSBackend"
