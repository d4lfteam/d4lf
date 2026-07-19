from unittest.mock import Mock

from src.overlay.widget.core import _OverlayCore


def test_save_settings_persists_relative_position_and_flags(monkeypatch):
    overlay = object.__new__(_OverlayCore)
    overlay.settings = {}
    overlay.winfo_x = Mock(return_value=110)
    overlay.winfo_y = Mock(return_value=220)
    overlay.locked = True
    overlay.capture_gold_stats = True
    overlay.capture_exp_stats = False
    overlay.show_gold = True
    overlay.font_size = 14
    overlay.wb_reference = None
    overlay.next_boss_name = "Unknown"
    overlay.orientation = "horizontal"
    overlay.font_family = "Consolas"
    overlay.settings = {"show_gold": True}
    monkeypatch.setattr("src.overlay.widget.core.game_window_roi", lambda: {"left": 10, "top": 20})
    saved = []
    monkeypatch.setattr("src.overlay.widget.core.save_info_settings", lambda values: saved.append(values))

    overlay._save_settings()

    assert saved[0]["x"] == 100
    assert saved[0]["y"] == 200
    assert saved[0]["show_gold"] is True
