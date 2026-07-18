from src.overlay._widget import BossTimerOverlay


def test_boss_timer_overlay_composes_actions_and_timer_behavior():
    overlay = object.__new__(BossTimerOverlay)
    overlay.locked = False
    overlay._on_lock_changed = lambda: None
    saved = []
    overlay._save_settings = lambda: saved.append(True)

    overlay._toggle_lock()

    assert overlay.locked
    assert saved == [True]
