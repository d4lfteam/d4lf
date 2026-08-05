from src.overlay.widget.widget import BossTimerOverlay


def test_toggle_lock_changes_state_and_persists_settings(monkeypatch):
    overlay = object.__new__(BossTimerOverlay)
    overlay.locked = False
    lock_changed_calls: list[bool] = []
    saved: list[bool] = []

    def on_lock_changed(_overlay: BossTimerOverlay) -> None:
        lock_changed_calls.append(True)

    def save_settings(_overlay: BossTimerOverlay) -> None:
        saved.append(True)

    monkeypatch.setattr(BossTimerOverlay, "_on_lock_changed", on_lock_changed)
    monkeypatch.setattr(BossTimerOverlay, "_save_settings", save_settings)

    overlay._toggle_lock()

    assert overlay.locked
    assert lock_changed_calls == [True]
    assert saved == [True]
