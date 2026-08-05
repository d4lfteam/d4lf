from src import overlay
from src.overlay import tracking as _tracking


def test_overlay_facade_exposes_lifecycle_and_tracking_contract():
    expected = {
        "InventoryExpTracker",
        "SessionStats",
        "is_open",
        "open_overlay",
        "request_close",
        "set_busy_checker",
        "update_stats",
    }
    assert expected <= set(overlay.__all__)
    assert all(hasattr(overlay, name) for name in expected)


def test_overlay_facade_delegates_busy_check(monkeypatch):
    overlay.set_busy_checker(lambda: True)

    assert _tracking._busy_checker()
