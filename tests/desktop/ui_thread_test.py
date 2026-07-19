import sys
import threading

import pytest

if sys.platform != "win32":
    pytest.skip("Windows-only: shared UI thread requires a non-main-thread Tk root", allow_module_level=True)

from src import desktop as ui_thread


def test_post_to_ui_thread_runs_on_shared_ui_thread() -> None:
    result = {}
    done = threading.Event()

    def record() -> None:
        result["thread"] = threading.current_thread()
        done.set()

    ui_thread.post_to_ui_thread(record)

    assert done.wait(timeout=2.0)
    assert result["thread"] is not threading.current_thread()
    assert result["thread"].name == "d4lf-ui-thread"


def test_call_on_ui_thread_returns_value() -> None:
    def add() -> int:
        assert threading.current_thread().name == "d4lf-ui-thread"
        return 1 + 1

    assert ui_thread.call_on_ui_thread(add) == 2


def test_call_on_ui_thread_propagates_exceptions() -> None:
    class BoomError(Exception):
        pass

    def raise_error() -> None:
        message = "boom"
        raise BoomError(message)

    with pytest.raises(BoomError):
        ui_thread.call_on_ui_thread(raise_error)


def test_get_root_returns_the_same_shared_root() -> None:
    assert ui_thread.get_root() is ui_thread.get_root()
