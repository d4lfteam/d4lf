import logging
import queue
import typing
from threading import Event
from typing import cast
from unittest.mock import Mock

if typing.TYPE_CHECKING:
    import pytest
    from pytest_mock import MockerFixture

    from src.loot.highlighting import HighlightTask, _VisionModeWithHighlighting

from src.item import Affix, FilterResult, Item, MatchedFilter
from src.loot.highlighting_render import HighlightingRenderer
from src.perception import LocatedMarker, LocatorResult
from src.settings import get_settings


class _RendererHarness(HighlightingRenderer):
    root: Mock
    canvas: Mock
    thick: int
    screen_off_x: int
    screen_off_y: int
    queue: queue.Queue[HighlightTask]
    current_item: Item | None


def test_highlighting_renderer_places_reliable_affix_markers(monkeypatch, mocker: MockerFixture) -> None:
    renderer = _RendererHarness()
    renderer.root = mocker.Mock()
    renderer.canvas = mocker.Mock()
    renderer.thick = 4
    renderer.screen_off_x = 0
    renderer.screen_off_y = 0
    monkeypatch.setattr(renderer, "create_signal_rect", mocker.Mock())
    monkeypatch.setattr(renderer, "draw_text", mocker.Mock(side_effect=lambda *_args: 1))
    draw_rect = Mock()
    monkeypatch.setattr(renderer, "draw_rect", draw_rect)
    cast("_VisionModeWithHighlighting", renderer).draw_match_outline(
        (10, 20, 100, 200),
        FilterResult(keep=True, matched=[MatchedFilter("Build")]),
        LocatorResult([LocatedMarker("affix", 0, (30, 40), 0.99)], reliable=True),
    )
    draw_rect.assert_called_once_with(renderer.canvas, 12, (30, 40), 10, "#23fc5d")


def test_highlighting_renderer_shows_missing_affixes_in_one_line_under_their_profile(
    monkeypatch, mocker: MockerFixture
) -> None:
    mocker.patch.object(get_settings().advanced_options, "max_missing_affixes_shown", 10)
    renderer = _RendererHarness()
    renderer.root = mocker.Mock()
    renderer.canvas = mocker.Mock()
    renderer.thick = 4
    renderer.screen_off_x = 0
    renderer.screen_off_y = 0
    monkeypatch.setattr(renderer, "create_signal_rect", mocker.Mock())
    drawn: list[tuple[str, str]] = []

    def _record_text(_canvas: Mock, text: str, color: str, text_y: int, _offset: int, _center: int) -> int:
        drawn.append((text, color))
        return text_y - 1

    monkeypatch.setattr(renderer, "draw_text", _record_text)
    cast("_VisionModeWithHighlighting", renderer).draw_match_outline(
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

    top_to_bottom = list(reversed(drawn))
    assert top_to_bottom == [
        ("Build.Helm", "#23fc5d"),
        ("missing: maximum_life, dexterity", "#8b2e2e"),
        ("Other.Helm", "#23fc5d"),
    ]


def test_draw_from_queue_reschedules_and_logs_when_drawing_fails(
    monkeypatch, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    item = Item(name="helm")
    renderer = _RendererHarness()
    renderer.canvas = mocker.Mock()
    renderer.queue = queue.Queue()
    renderer.current_item = item
    renderer.queue.put(("match", item, (0, 0, 10, 10), FilterResult(keep=True, matched=[]), None))
    monkeypatch.setattr(renderer, "draw_match_outline", mocker.Mock(side_effect=RuntimeError("boom")))

    with caplog.at_level(logging.ERROR, logger="src.loot.highlighting_render"):
        cast("_VisionModeWithHighlighting", renderer).draw_from_queue()

    renderer.canvas.after.assert_called_once_with(10, renderer.draw_from_queue)
    assert "Error while drawing highlighting overlay" in caplog.text
    assert "boom" in caplog.text


def test_draw_from_queue_reschedules_when_queue_is_empty(mocker: MockerFixture) -> None:
    renderer = _RendererHarness()
    renderer.canvas = mocker.Mock()
    renderer.queue = queue.Queue()

    cast("_VisionModeWithHighlighting", renderer).draw_from_queue()

    renderer.canvas.after.assert_called_once_with(10, renderer.draw_from_queue)


def test_draw_from_queue_sets_done_event_after_clearing_canvas(monkeypatch, mocker: MockerFixture) -> None:
    renderer = _RendererHarness()
    renderer.root = mocker.Mock()
    renderer.canvas = mocker.Mock()
    renderer.queue = queue.Queue()
    reset_canvas = mocker.Mock()
    monkeypatch.setattr("src.loot.highlighting_render.reset_canvas", reset_canvas)
    clear_done = Event()
    renderer.queue.put(("clear", clear_done))

    cast("_VisionModeWithHighlighting", renderer).draw_from_queue()

    reset_canvas.assert_called_once_with(renderer.root, renderer.canvas)
    assert clear_done.is_set()


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

    next_text_y = cast("_VisionModeWithHighlighting", _RendererHarness()).draw_text(
        canvas, "missing: cooldown_reduction, critical_strike_chance, resource_cost_reduction", "#fff", 456, 5, 216
    )

    canvas.bbox.assert_called_once_with("text")
    canvas.create_rectangle.assert_called_once_with(10, 400, 420, 451, fill="#111111", outline="")
    canvas.tag_lower.assert_called_once_with("background", "text")
    assert next_text_y == 400
