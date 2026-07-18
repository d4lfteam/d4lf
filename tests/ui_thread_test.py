import sys
import threading

import pytest

if sys.platform != "win32":
    # Tk on macOS requires its root be created on the main thread (Cocoa/NSWindow
    # restriction) — the shared UI thread here is deliberately a background thread,
    # which is fine on Windows (the app's actual target) but fatally crashes the
    # whole interpreter on macOS. Same reason paragon_overlay_test.py is skipped here.
    pytest.skip("Windows-only: shared UI thread requires a non-main-thread Tk root", allow_module_level=True)

from src import desktop as ui_thread


def test_post_to_ui_thread_runs_on_shared_ui_thread():
    result = {}
    done = threading.Event()

    def _record():
        result["thread"] = threading.current_thread()
        done.set()

    ui_thread.post_to_ui_thread(_record)

    assert done.wait(timeout=2.0)
    assert result["thread"] is not threading.current_thread()
    assert result["thread"].name == "d4lf-ui-thread"


def test_call_on_ui_thread_returns_value_from_the_ui_thread():
    def _add() -> int:
        assert threading.current_thread().name == "d4lf-ui-thread"
        return 1 + 1

    assert ui_thread.call_on_ui_thread(_add) == 2


def test_call_on_ui_thread_propagates_exceptions_to_the_caller():
    class BoomError(Exception):
        pass

    def _raise():
        msg = "boom"
        raise BoomError(msg)

    with pytest.raises(BoomError):
        ui_thread.call_on_ui_thread(_raise)


def test_get_root_returns_the_same_shared_root():
    assert ui_thread.get_root() is ui_thread.get_root()
