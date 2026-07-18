from unittest.mock import Mock

from src.item import FilterResult, MatchedFilter
from src.loot._highlighting_render import HighlightingRenderer
from src.perception import LocatedMarker, LocatorResult


def test_highlighting_renderer_places_reliable_affix_markers():
    renderer = object.__new__(HighlightingRenderer)
    renderer.root = Mock()
    renderer.canvas = Mock()
    renderer.thick = 4
    renderer.screen_off_x = 0
    renderer.screen_off_y = 0
    renderer.create_signal_rect = Mock()
    renderer.draw_text = Mock(side_effect=lambda *_args: 1)
    renderer.draw_rect = Mock()

    renderer.draw_match_outline(
        (10, 20, 100, 200),
        FilterResult(keep=True, matched=[MatchedFilter("Build")]),
        LocatorResult([LocatedMarker("affix", 0, (30, 40), 0.99)], reliable=True),
    )

    renderer.draw_rect.assert_called_once_with(renderer.canvas, 12, (30, 40), 10, "#23fc5d")
