from typing import TYPE_CHECKING, cast

from src.loot import get_filter_colors
from src.overlay.widget import controls as _controls
from src.overlay.widget.shared import ACCENT, MUTED, TEXT
from src.overlay.widget.widget import BossTimerOverlay

if TYPE_CHECKING:
    import tkinter as tk
    from collections.abc import Callable

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


_PARENT = cast("tk.Misc", object())


class _FakeButton:
    command: Callable[[], None]

    def __init__(self, _parent: tk.Misc, **kwargs: JsonValue) -> None:
        self.options: dict[str, JsonValue] = dict(kwargs)
        self.packed = False

    def config(self, command: Callable[[], None] | None = None, **kwargs: JsonValue) -> None:
        if command is not None:
            self.command = command
        self.options.update(kwargs)

    def pack(self, **_kwargs: JsonValue) -> None:
        self.packed = True

    def click(self) -> None:
        self.command()


def _fake(btn: tk.Button) -> _FakeButton:
    return cast("_FakeButton", btn)


def _overlay_with_fake_buttons(monkeypatch) -> tuple[BossTimerOverlay, list[str]]:
    overlay = object.__new__(BossTimerOverlay)
    overlay.font_family = "Arial"
    overlay.font_size = 10
    overlay.settings = {}
    events: list[str] = []
    monkeypatch.setattr(_controls.tk, "Button", _FakeButton)
    monkeypatch.setattr(_controls, "save_info_settings", lambda values: events.append(f"save:{values}"))
    monkeypatch.setattr(BossTimerOverlay, "_repack", lambda _self: events.append("repack"))
    monkeypatch.setattr(BossTimerOverlay, "_save_settings", lambda _self: events.append("save_settings"))
    return overlay, events


def test_attribute_toggle_flips_attribute_recolors_and_runs_callback(monkeypatch) -> None:
    overlay, events = _overlay_with_fake_buttons(monkeypatch)
    overlay.show_wb = False
    matched = get_filter_colors().matched

    btn = _fake(
        overlay._create_toggle_btn(_PARENT, "World Boss", "show_wb", callback=lambda: events.append("callback"))
    )

    assert btn.packed
    assert btn.options["fg"] == MUTED
    assert btn.options["activebackground"] == matched
    btn.click()
    assert overlay.show_wb is True
    assert btn.options["fg"] == matched
    assert events == ["callback", "repack", "save_settings"]


def test_config_toggle_persists_setting_and_uses_accent_background(monkeypatch) -> None:
    overlay, events = _overlay_with_fake_buttons(monkeypatch)
    overlay.settings["check_exp_on_inventory_open"] = True

    btn = _fake(overlay._create_config_toggle_btn(_PARENT, "Auto", "check_exp_on_inventory_open"))

    assert btn.options["fg"] == get_filter_colors().matched
    assert btn.options["activebackground"] == ACCENT
    btn.click()
    assert overlay.settings["check_exp_on_inventory_open"] is False
    assert btn.options["fg"] == MUTED
    assert events == ["save:{'check_exp_on_inventory_open': False}", "repack", "save_settings"]


def test_radio_button_marks_selection_with_indent(monkeypatch) -> None:
    overlay, _events = _overlay_with_fake_buttons(monkeypatch)

    btn = _fake(overlay._create_radio_button(_PARENT, "5m", 5, 5, lambda _value: None))

    assert btn.options["text"] == "● 5m"
    assert btn.options["padx"] == 20
    assert btn.options["fg"] == get_filter_colors().matched


def test_submenu_button_opens_submenu_with_itself(monkeypatch) -> None:
    overlay, _events = _overlay_with_fake_buttons(monkeypatch)
    opened: list[tuple[_FakeButton, str]] = []
    monkeypatch.setattr(
        BossTimerOverlay, "_open_submenu", lambda _self, btn, submenu_id, _builder: opened.append((btn, submenu_id))
    )

    btn = _fake(overlay._create_submenu_button(_PARENT, "Font", "font_submenu", lambda _popup: None))
    btn.click()

    assert btn.options["text"] == "Font ▶"
    assert btn.options["fg"] == TEXT
    assert opened == [(btn, "font_submenu")]
