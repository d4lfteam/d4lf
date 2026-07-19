import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows named-pipe adapter")


def test_windows_backend_module_is_only_exercised_on_windows() -> None:
    from src.perception.backend.windows import WindowsTTSBackend  # ruff:ignore[import-outside-top-level]

    assert WindowsTTSBackend.__name__ == "WindowsTTSBackend"
