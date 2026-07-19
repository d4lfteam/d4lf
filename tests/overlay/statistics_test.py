import time

from src.overlay import SessionStats
from src.overlay import statistics as _statistics


def test_experience_increments_and_reset_clears_session(monkeypatch):
    stats = SessionStats()
    stats.reset_exp()
    monkeypatch.setattr(_statistics, "load_settings", lambda: {"capture_gold_stats": False, "capture_exp_stats": True})
    monkeypatch.setattr(_statistics, "_notify", lambda **_: None)
    stats.on_info_stat("Level 10 Experience: 100 / 500")
    stats.start_time = time.time() - 3600
    stats.on_info_stat("Level 10 Experience: 250 / 500")
    assert stats.total_exp == 150
    stats.reset_exp()
    assert stats.total_exp == 0
    assert stats.last_exp is None


def test_gold_updates_only_after_three_monotonic_observations(monkeypatch):
    stats = SessionStats()
    stats.reset_gold()
    monkeypatch.setattr(_statistics, "load_settings", lambda: {"capture_gold_stats": True, "capture_exp_stats": False})
    monkeypatch.setattr(_statistics, "_notify", lambda **_: None)

    stats.on_info_stat("1,000 Gold")
    stats.on_info_stat("1,100 Gold")
    stats.on_info_stat("1,100 Gold")
    assert stats.total_gold == 0

    stats.on_info_stat("1,100 Gold")

    assert stats.total_gold == 100


def test_verified_totals_are_saved_and_restored_without_qsettings(monkeypatch):
    stored: dict[str, object] = {
        "capture_gold_stats": True,
        "capture_exp_stats": True,
        "session_total_gold": 50,
        "session_total_exp": 25,
    }
    monkeypatch.setattr(_statistics, "load_settings", lambda: dict(stored))
    monkeypatch.setattr(_statistics, "save_settings", lambda values: stored.update(values))
    notifications: list[dict[str, object]] = []
    monkeypatch.setattr(_statistics, "_notify", lambda **values: notifications.append(values))

    stats = _statistics._SessionStats()
    stats.on_info_stat("1,000 Gold")
    stats.on_info_stat("1,100 Gold")
    stats.on_info_stat("1,100 Gold")
    stats.on_info_stat("1,100 Gold")
    stats.on_info_stat("Level 10 Experience: 100 / 500")
    stats.on_info_stat("Level 10 Experience: 250 / 500")

    assert stored["session_total_gold"] == 150
    assert stored["session_total_exp"] == 175
    assert notifications[0] == {"total_gained": 50}
    assert notifications[1] == {"gph": 0, "total_gained": 150}
    assert notifications[2] == {"total_exp": 25, "t2l": "-"}
    restored = _statistics._SessionStats()
    assert restored.total_gold == 150
    assert restored.total_exp == 175
