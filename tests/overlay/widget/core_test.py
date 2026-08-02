import datetime
from typing import TYPE_CHECKING

from src.overlay.widget import core as _widget_core
from src.overlay.widget.widget import BossTimerOverlay

if TYPE_CHECKING:
    from src.overlay.settings import InfoSettingValue


def test_save_settings_persists_relative_position_and_flags(monkeypatch):
    overlay = object.__new__(BossTimerOverlay)
    overlay.settings = {"show_gold": True}
    overlay.locked = True
    overlay.capture_gold_stats = True
    overlay.capture_exp_stats = False
    overlay.show_gold = True
    overlay.font_size = 14
    overlay.wb_reference = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
    overlay.next_boss_name = "Unknown"
    overlay.orientation = "horizontal"
    overlay.font_family = "Consolas"
    saved: list[dict[str, InfoSettingValue]] = []

    def game_window_roi() -> dict[str, int]:
        return {"left": 10, "top": 20}

    def save_settings(values: dict[str, InfoSettingValue]) -> None:
        saved.append(values)

    def winfo_x(_overlay: BossTimerOverlay) -> int:
        return 110

    def winfo_y(_overlay: BossTimerOverlay) -> int:
        return 220

    monkeypatch.setattr(_widget_core, "game_window_roi", game_window_roi)
    monkeypatch.setattr(_widget_core, "save_info_settings", save_settings)
    monkeypatch.setattr(BossTimerOverlay, "winfo_x", winfo_x)
    monkeypatch.setattr(BossTimerOverlay, "winfo_y", winfo_y)

    overlay._save_settings()

    assert saved[0]["x"] == 100
    assert saved[0]["y"] == 200
    assert saved[0]["show_gold"] is True
