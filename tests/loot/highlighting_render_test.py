import logging
import typing

if typing.TYPE_CHECKING:
    import pytest
    from pytest_mock import MockerFixture, MockType

from src.item import Affix, FilterResult, Item, MatchedFilter
from src.loot.highlighting_pipeline import MatchCommand, NoMatchCommand
from src.loot.highlighting_render import HighlightingOverlay, draw_text
from src.perception import LocatedMarker, LocatorResult
from src.settings import get_settings

ITEM = Item(name="helm")


def _overlay(root: MockType, canvas: MockType, item: Item | None = ITEM) -> HighlightingOverlay:
    overlay = HighlightingOverlay(root, canvas, thick=4, screen_offset=(0, 0))
    overlay.current_item = item
    return overlay


def test_match_command_places_reliable_affix_markers(monkeypatch, mocker: MockerFixture) -> None:
    monkeypatch.setattr("src.loot.highlighting_render.draw_text", lambda *_args: 1)
    root, canvas = mocker.Mock(), mocker.Mock()
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

    def _record_text(_canvas: MockType, text: str, color: str, text_y: int, _center: int) -> int:
        drawn.append((text, color))
        return text_y - 1

    monkeypatch.setattr("src.loot.highlighting_render.draw_text", _record_text)
    root, canvas = mocker.Mock(), mocker.Mock()
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
    root, canvas = mocker.Mock(), mocker.Mock()
    overlay = _overlay(root, canvas, Item(name="boots"))

    overlay.draw(NoMatchCommand(ITEM, (0, 0, 10, 10)))

    reset_canvas.assert_not_called()
    canvas.create_rectangle.assert_not_called()


def test_clear_sets_done_event_once_canvas_is_cleared(monkeypatch, mocker: MockerFixture) -> None:
    reset_canvas = mocker.Mock()
    monkeypatch.setattr("src.loot.highlighting_render.reset_canvas", reset_canvas)
    root, canvas = mocker.Mock(), mocker.Mock()
    overlay = _overlay(root, canvas)

    done = overlay.clear()
    assert not done.is_set()
    overlay.draw_from_queue()

    reset_canvas.assert_called_once_with(root, canvas)
    assert done.is_set()


def test_draw_from_queue_draws_submitted_commands_in_order(monkeypatch, mocker: MockerFixture) -> None:
    monkeypatch.setattr("src.loot.highlighting_render.reset_canvas", mocker.Mock())
    root, canvas = mocker.Mock(), mocker.Mock()
    overlay = _overlay(root, canvas)
    drawn: list[str] = []
    monkeypatch.setattr(overlay, "draw", lambda command: drawn.append(type(command).__name__))

    overlay.submit(NoMatchCommand(ITEM, (0, 0, 10, 10)))
    overlay.clear()
    for _ in range(3):
        overlay.draw_from_queue()

    assert drawn == ["NoMatchCommand", "ClearCommand"]


def test_draw_from_queue_reschedules_and_logs_when_drawing_fails(
    monkeypatch, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr("src.loot.highlighting_render.reset_canvas", mocker.Mock(side_effect=RuntimeError("boom")))
    root, canvas = mocker.Mock(), mocker.Mock()
    overlay = _overlay(root, canvas)
    overlay.submit(NoMatchCommand(ITEM, (0, 0, 10, 10)))

    with caplog.at_level(logging.ERROR, logger="src.loot.highlighting_render"):
        overlay.draw_from_queue()

    canvas.after.assert_called_once_with(10, overlay.draw_from_queue)
    assert "Error while drawing highlighting overlay" in caplog.text
    assert "boom" in caplog.text


def test_draw_from_queue_reschedules_when_queue_is_empty(mocker: MockerFixture) -> None:
    root, canvas = mocker.Mock(), mocker.Mock()
    overlay = _overlay(root, canvas)

    overlay.draw_from_queue()

    canvas.after.assert_called_once_with(10, overlay.draw_from_queue)


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
