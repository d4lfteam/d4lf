import typing
from unittest.mock import Mock

import numpy as np

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

from src.item import Affix, FilterResult, Item, MatchedFilter
from src.loot.highlighting_pipeline import MatchCommand, NoMatchCommand
from src.loot.highlighting_render import HighlightingVisionMode, draw_text
from src.perception import LocatedMarker, LocatorResult
from src.settings import get_settings

ITEM = Item(name="helm")


def _overlay(root: Mock, canvas: Mock, item: Item | None = ITEM) -> HighlightingVisionMode:
    overlay = HighlightingVisionMode(root, canvas, 4, (0, 0), np.array([[0, 0]]), np.array([[0, 0]]))
    overlay.current_item = item
    return overlay


def test_match_command_places_reliable_affix_markers(monkeypatch) -> None:
    monkeypatch.setattr("src.loot.highlighting_render.draw_text", lambda *_args: 1)
    root, canvas = Mock(), Mock()
    overlay = _overlay(root, canvas)

    overlay.draw(
        MatchCommand(
            ITEM,
            (10, 20, 100, 200),
            FilterResult(keep=True, matched=[MatchedFilter("Build")]),
            LocatorResult([LocatedMarker("affix", 0, (30, 40), 0.99)], reliable=True),
        )
    )

    canvas.create_rectangle.assert_any_call(34, 44, 46, 56, fill="#23fc5d")
    root.geometry.assert_called_with("120x250+0+10")


def test_match_command_shows_missing_affixes_in_one_line_under_their_profile(
    monkeypatch, mocker: MockerFixture
) -> None:
    mocker.patch.object(get_settings().advanced_options, "max_missing_affixes_shown", 10)
    drawn: list[tuple[str, str]] = []

    def _record_text(_canvas: Mock, text: str, color: str, text_y: int, _center: int) -> int:
        drawn.append((text, color))
        return text_y - 1

    monkeypatch.setattr("src.loot.highlighting_render.draw_text", _record_text)
    root, canvas = Mock(), Mock()
    overlay = _overlay(root, canvas)

    overlay.draw(
        MatchCommand(
            ITEM,
            (10, 20, 100, 200),
            FilterResult(
                keep=True,
                matched=[
                    MatchedFilter("Build.Helm", [Affix(name="armor")], missing_affixes=["maximum_life", "dexterity"]),
                    MatchedFilter("Other.Helm", [Affix(name="armor")]),
                ],
            ),
            None,
        )
    )

    assert list(reversed(drawn)) == [
        ("Build.Helm", "#23fc5d"),
        ("missing: maximum_life, dexterity", "#8b2e2e"),
        ("Other.Helm", "#23fc5d"),
    ]


def test_command_for_stale_item_is_skipped(monkeypatch, mocker: MockerFixture) -> None:
    reset_canvas = mocker.Mock()
    monkeypatch.setattr("src.loot.highlighting_render.reset_canvas", reset_canvas)
    root, canvas = Mock(), Mock()
    overlay = _overlay(root, canvas, Item(name="boots"))

    overlay.draw(NoMatchCommand(ITEM, (0, 0, 10, 10)))

    reset_canvas.assert_not_called()
    canvas.create_rectangle.assert_not_called()


def test_clear_sets_done_event_once_canvas_is_cleared(monkeypatch, mocker: MockerFixture) -> None:
    reset_canvas = mocker.Mock()
    monkeypatch.setattr("src.loot.highlighting_render.reset_canvas", reset_canvas)
    root, canvas = Mock(), Mock()
    overlay = _overlay(root, canvas)

    done = overlay.clear()
    assert not done.is_set()
    overlay.draw_from_queue()

    reset_canvas.assert_called_once_with(root, canvas)
    assert done.is_set()


def test_on_tts_delegates_to_worker() -> None:
    overlay = _overlay(Mock(), Mock())
    overlay.worker = Mock()

    overlay.on_tts(["line"])

    overlay.worker.on_tts.assert_called_once_with(["line"])


def test_on_stop_clears_overlay_and_stops_worker(monkeypatch) -> None:
    overlay = _overlay(Mock(), Mock())
    overlay.worker = Mock()
    clear = Mock()
    monkeypatch.setattr(overlay, "clear", clear)

    overlay.on_stop()

    clear.assert_called_once_with()
    overlay.worker.stop.assert_called_once_with()


def test_overlay_window_starts_hidden() -> None:
    root = Mock()

    HighlightingVisionMode(root, Mock(), 4, (0, 0), np.array([[0, 0]]), np.array([[0, 0]]))

    root.geometry.assert_called_once_with("0x0+0+0")


def test_draw_text_positions_background_and_next_label_from_rendered_bounds(monkeypatch, mocker: MockerFixture) -> None:
    font = mocker.Mock()
    font.measure.side_effect = lambda text: 9 * len(text)
    monkeypatch.setattr("src.loot.highlighting_render.Font", mocker.Mock(return_value=font))
    monkeypatch.setattr(
        "src.loot.highlighting_render.get_ui_coordinates",
        mocker.Mock(return_value=mocker.Mock(pos=mocker.Mock(window_dimensions=(1920, 1080)))),
    )
    canvas = mocker.Mock()
    canvas.create_text.return_value = "text"
    canvas.create_rectangle.return_value = "background"
    # Word wrapping rendered three lines where a character-count estimate would reserve two
    canvas.bbox.return_value = (10, 400, 420, 451)

    next_text_y = draw_text(
        canvas, "missing: cooldown_reduction, critical_strike_chance, resource_cost_reduction", "#fff", 456, 216
    )

    canvas.bbox.assert_called_once_with("text")
    canvas.create_rectangle.assert_called_once_with(10, 400, 420, 451, fill="#111111", outline="")
    canvas.tag_lower.assert_called_once_with("background", "text")
    assert next_text_y == 400
