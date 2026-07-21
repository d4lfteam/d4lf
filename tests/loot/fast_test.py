import tkinter as tk
import typing
from types import SimpleNamespace
from typing import Any, cast

import pytest

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

import src.loot.fast as fast_module
from src.item import FilterResult, Item, ItemRarity, MatchedFilter
from src.loot.fast import VisionModeFast, create_match_text, fast_feedback


class _DestroyableText:
    def __init__(self) -> None:
        self.destroyed = False

    def destroy(self) -> None:
        if self.destroyed:
            message = "invalid command name .text"
            raise tk.TclError(message)
        self.destroyed = True


class _MeasuredText:
    def __init__(self) -> None:
        self.placements: list[dict[str, int]] = []

    def config(self, **_kwargs: object) -> None:
        pass

    def update_idletasks(self) -> None:
        pass

    def get(self, _start: float, _end: str) -> str:
        return "test.Affixes.Test\n  - maximum_life\n  - strength\n"

    def tag_cget(self, _tag: str, _option: str) -> str:
        return "Courier New 20"

    def cget(self, _option: str) -> str:
        return "Courier New 20"

    def place_configure(self, **kwargs: int) -> None:
        self.placements.append(kwargs)

    def place(self, **kwargs: int) -> None:
        self.placements.append(kwargs)


def test_fast_mode_preserves_match_details_and_feedback():
    assert create_match_text([MatchedFilter("Build", aspect_match=True, set_match=True)]) == [
        "Build\n  - Aspect\n  - Set"
    ]
    assert fast_feedback(Item(), FilterResult(keep=False, matched=[])) is None
    assert fast_feedback(Item(rarity=ItemRarity.Unique), FilterResult(keep=True, matched=[])) == ("Unique", "#23fc5d")


def test_fast_mode_clears_unmatched_items_without_drawing(monkeypatch, mocker: MockerFixture) -> None:
    wrapped = cast("Any", VisionModeFast)
    mode_type = next(cell.cell_contents for cell in wrapped.__closure__ if isinstance(cell.cell_contents, type))
    mode = object.__new__(mode_type)
    mode.request_clear = mocker.Mock()
    mode.request_draw = mocker.Mock()

    monkeypatch.setattr(fast_module, "is_ignored_item", lambda _item: False)
    monkeypatch.setattr(fast_module.src.perception, "read_latest_item", lambda: Item())
    monkeypatch.setattr(
        fast_module,
        "Filter",
        lambda: type("_Filter", (), {"should_keep": lambda _self, _item: FilterResult(keep=False, matched=[])})(),
    )

    mode.on_tts(None)

    mode.request_clear.assert_called_once_with()
    mode.request_draw.assert_not_called()


def test_clearing_before_next_match_does_not_leave_a_dead_textbox() -> None:
    wrapped = cast("Any", VisionModeFast)
    mode_type = next(cell.cell_contents for cell in wrapped.__closure__ if isinstance(cell.cell_contents, type))
    mode = object.__new__(mode_type)
    mode.textbox = _DestroyableText()

    mode.clear_textbox()

    mode.clear_textbox()

    assert mode.textbox is None


def test_fast_match_textbox_gets_content_sized_geometry(monkeypatch) -> None:
    wrapped = cast("Any", VisionModeFast)
    mode_type = next(cell.cell_contents for cell in wrapped.__closure__ if isinstance(cell.cell_contents, type))
    mode = object.__new__(mode_type)
    textbox = _MeasuredText()
    mode.textbox = textbox

    class _Font:
        def metrics(self, _metric: str) -> int:
            return 20

        def measure(self, value: str) -> int:
            return 170 if value == "  - maximum_life" else 10

    monkeypatch.setattr(fast_module.font, "Font", lambda **_kwargs: _Font())
    mode.adjust_textbox_size()

    placement = textbox.placements[-1]
    assert placement["width"] == 174
    assert placement["height"] == 60


@pytest.mark.parametrize(("configured", "expected"), [(None, (1920.0, 1440.0)), ((300, 500), (300, 500))])
def test_fast_textbox_uses_configured_position_or_centered_default(monkeypatch, configured, expected) -> None:
    wrapped = cast("Any", VisionModeFast)
    mode_type = next(cell.cell_contents for cell in wrapped.__closure__ if isinstance(cell.cell_contents, type))
    mode = object.__new__(mode_type)
    textbox = _MeasuredText()
    mode.root = object()
    mode.textbox = None

    monkeypatch.setattr(fast_module, "Font", lambda **_kwargs: object())
    monkeypatch.setattr(fast_module.tk, "Text", lambda *_args, **_kwargs: textbox)
    monkeypatch.setattr(fast_module, "get_ui_coordinates", lambda: SimpleNamespace(resolution=(3840, 2160)))
    monkeypatch.setattr(
        fast_module,
        "get_settings",
        lambda: SimpleNamespace(
            general=SimpleNamespace(minimum_overlay_font_size=12),
            advanced_options=SimpleNamespace(fast_vision_mode_coordinates=configured),
        ),
    )

    mode.create_textbox()

    assert textbox.placements[-1] == {"x": expected[0], "y": expected[1]}
