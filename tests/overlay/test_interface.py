from src import overlay


def test_overlay_facade_exposes_lifecycle_and_tracking_contract():
    expected = {
        "InventoryExpTracker",
        "SessionStats",
        "is_info_overlay_open",
        "open_boss_timer_overlay",
        "request_close",
        "set_busy_checker",
        "update_stats",
    }
    assert expected <= set(overlay.__all__)
    assert all(hasattr(overlay, name) for name in expected)
