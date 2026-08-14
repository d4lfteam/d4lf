from typing import TYPE_CHECKING

from src.overlay.widget.widget import BossTimerOverlay

if TYPE_CHECKING:
    from src.type_aliases import JsonValue


class _Frame:
    config_calls: list[dict[str, JsonValue]]

    def __init__(self) -> None:
        self.config_calls = []

    def config(self, **kwargs: JsonValue) -> None:
        self.config_calls.append(kwargs)


def test_toggle_orientation_repackages_and_persists(monkeypatch) -> None:
    overlay = object.__new__(BossTimerOverlay)
    overlay.orientation = "horizontal"
    frame = _Frame()
    repack_calls: list[bool] = []
    saved: list[bool] = []

    def repack(_overlay: BossTimerOverlay) -> None:
        repack_calls.append(True)

    def save_settings(_overlay: BossTimerOverlay) -> None:
        saved.append(True)

    monkeypatch.setattr(BossTimerOverlay, "_repack", repack)
    monkeypatch.setattr(BossTimerOverlay, "_save_settings", save_settings)
    monkeypatch.setattr(BossTimerOverlay, "overlay_frame", frame, raising=False)

    overlay._toggle_orientation()

    assert overlay.orientation == "vertical"
    assert len(frame.config_calls) == 1
    assert repack_calls == [True]
    assert saved == [True]
