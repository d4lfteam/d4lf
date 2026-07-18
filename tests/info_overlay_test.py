import sys
import threading
import tkinter as tk
from typing import override

import pytest

if sys.platform != "win32":
    pytest.skip("Windows-only overlay test", allow_module_level=True)

from src import overlay


class _FakeOverlay(tk.Toplevel):
    """Stand-in for BossTimerOverlay: same singleton contract, none of the game-specific setup."""

    instances_created = 0

    def __init__(self, parent):
        super().__init__(parent)
        self.withdraw()
        _FakeOverlay.instances_created += 1

    @override
    def destroy(self):
        super().destroy()
        overlay._lifecycle._forget(self)


@pytest.fixture(autouse=True)
def _fake_boss_timer_overlay(monkeypatch):
    _FakeOverlay.instances_created = 0
    monkeypatch.setattr(overlay._lifecycle, "BossTimerOverlay", _FakeOverlay)
    yield
    overlay.request_close()
    overlay._lifecycle._forget(None)


def test_toggle_off_on_twice_never_leaves_two_live_instances():
    for _ in range(2):
        overlay.open_boss_timer_overlay()
        assert overlay.is_info_overlay_open()

        overlay.request_close()
        assert not overlay.is_info_overlay_open()

    assert _FakeOverlay.instances_created == 2


def test_concurrent_open_requests_only_create_one_instance():
    barrier = threading.Barrier(5)

    def _try_open():
        barrier.wait()
        overlay.open_boss_timer_overlay()

    threads = [threading.Thread(target=_try_open) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert overlay.is_info_overlay_open()
    assert _FakeOverlay.instances_created == 1


def test_request_close_without_an_open_overlay_is_a_no_op():
    overlay.request_close()
    assert not overlay.is_info_overlay_open()
