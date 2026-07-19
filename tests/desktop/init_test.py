import sys

import pytest

if sys.platform != "win32":
    pytest.skip("Windows-only: shared UI thread requires a non-main-thread Tk root", allow_module_level=True)

from src import desktop


def test_desktop_facade_exports_ui_thread_helpers() -> None:
    helpers = (
        "call_on_ui_thread",
        "create_overlay_toplevel",
        "get_root",
        "is_alive",
        "join_ui_thread",
        "post_to_ui_thread",
    )
    for name in helpers:
        assert callable(getattr(desktop, name))

    assert desktop.call_on_ui_thread(lambda: "ok") == "ok"
