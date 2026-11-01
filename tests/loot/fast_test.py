import tkinter as tk
import typing
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

if typing.TYPE_CHECKING:
    from tkinter.font import Font

    from pytest_mock import MockerFixture

import src.loot.fast as fast_module
from src.game_data import ItemRarity
from src.item import Affix, FilterResult, Item, MatchedFilter
from src.loot.fast import FastVisionMode, create_match_text, fast_feedback
from src.settings import get_settings


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
        self.placements: list[dict[str, int | float]] = []

    def config(self, **_kwargs: str | float | bool | None) -> None:
        pass

    def update_idletasks(self) -> None:
        pass

    def get(self, _start: float, _end: str) -> str:
        return "test.Affixes.Test\n  - maximum_life\n  - strength\n"

    def tag_cget(self, _tag: str, _option: str) -> str:
        return "Courier New 20"

    def cget(self, _option: str) -> str:
        return "Courier New 20"

    def place_configure(self, **kwargs: float) -> None:
        self.placements.append(kwargs)

    def place(self, **kwargs: float) -> None:
        self.placements.append(kwargs)


def _new_fast_mode() -> FastVisionMode:
    return FastVisionMode(Mock(), Mock())


def test_fast_mode_preserves_match_details_and_feedback() -> None:
    assert create_match_text([MatchedFilter("Build", aspect_match=True, set_match=True)], "green", "red") == [
        ("Build", "green"),
        ("  - Aspect", "green"),
        ("  - Set", "green"),
    ]
    assert fast_feedback(Item(), FilterResult(keep=False, matched=[])) is None
    assert fast_feedback(Item(rarity=ItemRarity.Unique), FilterResult(keep=True, matched=[])) == [("Unique", "#23fc5d")]


def test_fast_mode_lists_missing_affixes_after_matched_ones_in_missing_color(mocker: MockerFixture) -> None:
    mocker.patch.object(get_settings().advanced_options, "max_missing_affixes_shown", 10)
    match = MatchedFilter("Build.Helm", [Affix(name="armor")], missing_affixes=["maximum_life"])

    assert create_match_text([match], "green", "red") == [
        ("Build.Helm", "green"),
        ("  - armor", "green"),
        ("  - maximum_life", "red"),
    ]


def test_fast_mode_has_no_result_for_a_skipped_item() -> None:
    assert fast_feedback(Item(), FilterResult(keep=False, matched=[], skipped=True)) is None


def test_fast_mode_omits_redundant_aspect_for_always_kept_mythics() -> None:
    assert fast_feedback(
        Item(rarity=ItemRarity.Mythic),
        FilterResult(keep=True, matched=[MatchedFilter("Mythics always kept", aspect_match=True)]),
    ) == [("Mythics always kept", "#23fc5d")]


def test_fast_mode_clears_unmatched_items_without_drawing(monkeypatch, mocker: MockerFixture) -> None:
    mode = _new_fast_mode()
    mode.request_clear = mocker.Mock()
    mode.request_draw = mocker.Mock()

    monkeypatch.setattr(fast_module, "is_ignored_item", lambda _item: False)
    monkeypatch.setattr(fast_module.src.perception, "read_latest_item", Item)
    monkeypatch.setattr(
        fast_module,
        "Filter",
        type("_Filter", (), {"should_keep": lambda _self, _item: FilterResult(keep=False, matched=[])}),
    )

    mode.on_tts([])

    mode.request_clear.assert_called_once_with()
    mode.request_draw.assert_not_called()


def test_clearing_before_next_match_does_not_leave_a_dead_textbox() -> None:
    mode = _new_fast_mode()
    mode.textbox = typing.cast("tk.Text", _DestroyableText())

    mode.clear_textbox()

    mode.clear_textbox()

    assert mode.textbox is None


def test_fast_match_textbox_gets_content_sized_geometry(monkeypatch) -> None:
    mode = _new_fast_mode()
    textbox = _MeasuredText()
    mode.textbox = typing.cast("tk.Text", textbox)

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
    mode = _new_fast_mode()
    textbox = _MeasuredText()
    mode.root = typing.cast("tk.Toplevel", object())
    mode.textbox = None

    monkeypatch.setattr(fast_module, "Font", lambda **_kwargs: typing.cast("Font", object()))
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


def test_draw_dispatches_text_and_clear(mocker: MockerFixture) -> None:
    mode = _new_fast_mode()
    insert = mocker.patch.object(mode, "insert_colored_lines")
    clear = mocker.patch.object(mode, "clear_textbox")

    mode.draw(("text", [("Build", "green")]))
    insert.assert_called_once_with([("Build", "green")])
    clear.assert_not_called()

    mode.draw(("clear",))
    clear.assert_called_once_with()


def test_on_stop_queues_a_clear(mocker: MockerFixture) -> None:
    mode = _new_fast_mode()
    clear = mocker.patch.object(mode, "clear_textbox")

    mode.on_stop()
    mode.draw_from_queue()

    clear.assert_called_once_with()
