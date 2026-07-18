from src.overlay._widget_actions import _OverlayActions


def test_toggle_lock_changes_state_and_persists_settings():
    overlay = object.__new__(_OverlayActions)
    overlay.locked = False
    overlay._on_lock_changed = lambda: None
    saved = []
    overlay._save_settings = lambda: saved.append(True)

    overlay._toggle_lock()

    assert overlay.locked
    assert saved == [True]
