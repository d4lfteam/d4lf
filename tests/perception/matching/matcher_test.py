import cv2
import numpy as np
import pytest

from src.perception.matching.matcher import find_image_matches, get_cv_result
from src.settings import Template


def test_find_image_matches_returns_image_coordinates_without_monitor_state() -> None:
    template_image = np.array([[[10, 20, 30], [40, 50, 60]], [[70, 80, 90], [100, 110, 120]]], dtype=np.uint8)
    image = np.zeros((10, 12, 3), dtype=np.uint8)
    image[4:6, 5:7] = template_image
    template = Template(name="marker", img_bgr=template_image)

    matches = find_image_matches(template, image, None, None, False, 0.99)

    assert matches
    assert matches[0].region == (5, 4, 2, 2)
    assert matches[0].score == pytest.approx(1.0)


def test_get_cv_result_keeps_roi_offset_in_result_metadata() -> None:
    template_image = np.array([[[10, 20, 30], [40, 50, 60]]], dtype=np.uint8)
    image = np.zeros((8, 10, 3), dtype=np.uint8)
    image[3:4, 4:6] = template_image
    template = Template(img_bgr=template_image)

    result, prepared_template, resolved_roi = get_cv_result(template, image, [2, 2, 6, 4])

    assert result is not None
    assert prepared_template.shape == template_image.shape
    assert resolved_roi == [2, 2, 6, 4]
    _, score, _, position = cv2.minMaxLoc(result)
    assert position == (2, 1)
    assert score == pytest.approx(1.0)
