import sys
import threading
import tkinter as tk
from typing import TYPE_CHECKING, cast, override

import pytest

from src.overlay import lifecycle as _lifecycle
from src.overlay import state as _state

if TYPE_CHECKING:
    from src.overlay.widget.widget import BossTimerOverlay


class _FakeOverlay:
    instances_created = 0

    def __init__(self, _parent, **_kwargs) -> None:
        type(self).instances_created += 1
        self.destroyed = False

    def winfo_exists(self) -> bool:
        return not self.destroyed

    def destroy(self) -> None:
        self.destroyed = True


def test_close_clears_shared_instance_and_allows_reopen(monkeypatch) -> None:
    _FakeOverlay.instances_created = 0
    monkeypatch.setattr(_lifecycle, "BossTimerOverlay", _FakeOverlay)
    monkeypatch.setattr(_lifecycle, "get_root", lambda: object())
    monkeypatch.setattr(_lifecycle, "call_on_ui_thread", lambda callback: callback())
    _state.clear_overlay()
    _lifecycle.open_overlay()
    _lifecycle.request_close()
    _lifecycle.open_overlay()
    assert _FakeOverlay.instances_created == 2
    assert _lifecycle.is_open()
    _lifecycle.request_close()


class _WindowsFakeOverlay(tk.Toplevel):
    instances_created = 0

    def __init__(self, parent, **_kwargs) -> None:
        super().__init__(parent)
        self.withdraw()
        type(self).instances_created += 1

    @override
    def destroy(self) -> None:
        super().destroy()
        _lifecycle._forget(cast("BossTimerOverlay", self))


@pytest.fixture
def fake_windows_overlay(monkeypatch):
    _WindowsFakeOverlay.instances_created = 0
    monkeypatch.setattr(_lifecycle, "BossTimerOverlay", _WindowsFakeOverlay)
    yield
    _lifecycle.request_close()
    _lifecycle._forget(None)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only overlay test")
def test_toggle_off_on_twice_never_leaves_two_live_instances(fake_windows_overlay) -> None:
    for _ in range(2):
        _lifecycle.open_overlay()
        assert _lifecycle.is_open()

        _lifecycle.request_close()
        assert not _lifecycle.is_open()

    assert _WindowsFakeOverlay.instances_created == 2


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only overlay test")
def test_concurrent_open_requests_only_create_one_instance(fake_windows_overlay) -> None:
    barrier = threading.Barrier(5)

    def try_open() -> None:
        barrier.wait()
        _lifecycle.open_overlay()

    threads = [threading.Thread(target=try_open) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert _lifecycle.is_open()
    assert _WindowsFakeOverlay.instances_created == 1


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only overlay test")
def test_request_close_without_an_open_overlay_is_a_no_op(fake_windows_overlay) -> None:
    _lifecycle.request_close()

    assert not _lifecycle.is_open()
