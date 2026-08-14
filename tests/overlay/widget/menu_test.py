from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.overlay.widget import menu as _widget_menu
from src.overlay.widget.widget import BossTimerOverlay

if TYPE_CHECKING:
    from src.type_aliases import JsonValue


class _FakeWidget:
    geometry_value: str | None

    def __init__(self, *_args: JsonValue, **_kwargs: JsonValue) -> None:
        self.geometry_value = None

    def overrideredirect(self, *, boolean: bool) -> None:
        pass

    def attributes(self, *_args: JsonValue, **_kwargs: JsonValue) -> None:
        pass

    def configure(self, **_kwargs: JsonValue) -> None:
        pass

    def geometry(self, value: str) -> None:
        self.geometry_value = value

    def pack(self, **_kwargs: JsonValue) -> _FakeWidget:
        return self

    def bind(self, *_args: JsonValue, **_kwargs: JsonValue) -> None:
        pass

    def focus_set(self) -> None:
        pass


@dataclass
class _PointerEvent:
    x_root: int
    y_root: int


def test_context_menu_records_pointer_position(monkeypatch) -> None:
    created_popups: list[_FakeWidget] = []

    def widget_factory(*_args: JsonValue, **_kwargs: JsonValue) -> _FakeWidget:
        return _FakeWidget()

    def toplevel_factory(*_args: JsonValue, **_kwargs: JsonValue) -> _FakeWidget:
        popup = _FakeWidget()
        created_popups.append(popup)
        return popup

    def noop(*_args: JsonValue, **_kwargs: JsonValue) -> None:
        pass

    monkeypatch.setattr(_widget_menu.tk, "Toplevel", toplevel_factory)
    monkeypatch.setattr(_widget_menu.tk, "Frame", widget_factory)
    monkeypatch.setattr(_widget_menu.tk, "Label", widget_factory)
    monkeypatch.setattr(_widget_menu.tk, "Button", widget_factory)
    for name in ("_create_toggle_btn", "_create_config_toggle_btn", "_create_radio_button", "_create_submenu_button"):
        monkeypatch.setattr(BossTimerOverlay, name, widget_factory)
    for name in (
        "_destroy_settings_popup",
        "_on_popup_focus_out",
        "_close_all_submenus",
        "_auto_sync",
        "_toggle_lock",
        "_change_size",
        "_toggle_orientation",
        "_change_font_family",
        "_reset_gold_stats",
        "_reset_exp_stats",
        "_pick_exp_bar_pos",
        "_reset_exp_bar_pos",
    ):
        monkeypatch.setattr(BossTimerOverlay, name, noop)

    overlay = object.__new__(BossTimerOverlay)
    overlay.font_family = "Consolas"
    overlay.font_size = 14
    overlay.orientation = "horizontal"
    overlay.locked = False
    overlay.settings = {"exp_bar_pos": None, "exp_age_before_refresh": 5}
    monkeypatch.setattr(BossTimerOverlay, "FONT_CHOICES", ("Consolas",), raising=False)
    overlay.show_wb = overlay.show_legion = overlay.show_ht = True
    overlay.capture_gold_stats = overlay.capture_exp_stats = False
    overlay.show_gph = overlay.show_total_gold = True
    overlay.show_eph = overlay.show_total_exp = overlay.show_t2l = overlay.show_next_scan = True
    overlay._last_menu_pos = (100, 100)

    overlay._show_context_menu(_PointerEvent(x_root=320, y_root=240))

    assert overlay._last_menu_pos == (320, 240)
    assert created_popups[0].geometry_value == "+320+240"
