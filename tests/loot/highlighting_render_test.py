import typing

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

from src.item import FilterResult, MatchedFilter
from src.loot.highlighting_render import HighlightingRenderer
from src.perception import LocatedMarker, LocatorResult


def test_highlighting_renderer_places_reliable_affix_markers(mocker: MockerFixture):
    renderer = object.__new__(HighlightingRenderer)
    renderer.root = mocker.Mock()
    renderer.canvas = mocker.Mock()
    renderer.thick = 4
    renderer.screen_off_x = 0
    renderer.screen_off_y = 0
    renderer.create_signal_rect = mocker.Mock()
    renderer.draw_text = mocker.Mock(side_effect=lambda *_args: 1)
    renderer.draw_rect = mocker.Mock()
    renderer.draw_match_outline(
        (10, 20, 100, 200),
        FilterResult(keep=True, matched=[MatchedFilter("Build")]),
        LocatorResult([LocatedMarker("affix", 0, (30, 40), 0.99)], reliable=True),
    )
    renderer.draw_rect.assert_called_once_with(renderer.canvas, 12, (30, 40), 10, "#23fc5d")
