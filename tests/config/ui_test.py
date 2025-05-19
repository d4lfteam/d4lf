import numpy as np
import pytest
from natsort import natsorted

from src.config.data import COLORS
from src.config.ui import ResManager, _ResTransformer

_PIXELS = [np.array([0, 0]), np.array([3840, 0]), np.array([0, 2160]), np.array([3840, 2160])]
_TESTS = [
    ("1920x1080", (np.array(coord) for coord in [(0, 0), (1920, 0), (0, 1080), (1920, 1080)])),
    ("1920x540", (np.array(coord) for coord in [(150, 0), (1770, 0), (150, 540), (1770, 540)])),
    ("2560x1080", (np.array(coord) for coord in [(0, 0), (2560, 0), (0, 1080), (2560, 1080)])),
    ("2560x1440", (np.array(coord) for coord in [(0, 0), (2560, 0), (0, 1440), (2560, 1440)])),
    ("2560x1600", (np.array(coord) for coord in [(0, 0), (2560, 0), (0, 1600), (2560, 1600)])),
    ("2560x720", (np.array(coord) for coord in [(200, 0), (2360, 0), (200, 720), (2360, 720)])),
    ("3440x1440", (np.array(coord) for coord in [(0, 0), (3440, 0), (0, 1440), (3440, 1440)])),
    ("3840x1080", (np.array(coord) for coord in [(300, 0), (3540, 0), (300, 1080), (3540, 1080)])),
    ("3840x1600", (np.array(coord) for coord in [(0, 0), (3840, 0), (0, 1600), (3840, 1600)])),
    ("3840x2160", (np.array(coord) for coord in [(0, 0), (3840, 0), (0, 2160), (3840, 2160)])),
    ("5120x1440", (np.array(coord) for coord in [(400, 0), (4720, 0), (400, 1440), (4720, 1440)])),
]


@pytest.mark.parametrize("res", natsorted([x[0] for x in _TESTS]), ids=natsorted([x[0] for x in _TESTS]))
def test_set_resolution(res):
    ResManager().set_resolution(res)
    assert ResManager().pos


@pytest.mark.parametrize("result", _TESTS, ids=[x[0] for x in _TESTS])
def test_transformation(result):
    for pixel in _PIXELS:
        new_pixel = _ResTransformer(result[0])._transform_array(pixel)
        expected = next(result[1])
        assert new_pixel[0] == expected[0]
        assert new_pixel[1] == expected[1]


def test_colors():
    assert COLORS is not None


def test_templates():
    assert len(ResManager().templates) == 53
