import numpy as np

from src.tools.replay.common import font_scale, parse_resolution


def test_parse_resolution_and_font_scale() -> None:
    assert parse_resolution("1920x1080") == (1920, 1080)
    small = font_scale(np.zeros((400, 800, 3), dtype=np.uint8))
    large = font_scale(np.zeros((800, 1600, 3), dtype=np.uint8))

    assert large > small
