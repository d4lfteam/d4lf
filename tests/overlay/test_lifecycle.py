from src.overlay import _lifecycle


class _FakeOverlay:
    instances_created = 0

    def __init__(self, _parent):
        type(self).instances_created += 1
        self.destroyed = False

    def winfo_exists(self):
        return not self.destroyed

    def destroy(self):
        self.destroyed = True


def test_close_clears_shared_instance_and_allows_reopen(monkeypatch):
    _FakeOverlay.instances_created = 0
    monkeypatch.setattr(_lifecycle, "BossTimerOverlay", _FakeOverlay)
    monkeypatch.setattr(_lifecycle, "get_root", lambda: object())
    monkeypatch.setattr(_lifecycle, "call_on_ui_thread", lambda callback: callback())
    _lifecycle._widget_shared._OVERLAY_INSTANCE = None

    _lifecycle.open_overlay()
    _lifecycle.request_close()
    _lifecycle.open_overlay()

    assert _FakeOverlay.instances_created == 2
    assert _lifecycle.is_open()
    _lifecycle.request_close()
