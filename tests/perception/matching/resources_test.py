from types import SimpleNamespace

import numpy as np
import pytest

from src.perception.matching.resources import process_template_refs, resolve_color_match, resolve_roi
from src.settings import Template


def test_resolve_roi_accepts_inline_values() -> None:
    assert resolve_roi((1, 2, 30, 40)) == [1.0, 2.0, 30.0, 40.0]


def test_resolve_roi_resolves_named_values(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.perception.matching.resources.get_ui_coordinates",
        lambda: SimpleNamespace(roi=SimpleNamespace(search=np.array([1, 2, 30, 40]))),
    )

    assert resolve_roi("search") == [1.0, 2.0, 30.0, 40.0]


def test_resolve_roi_rejects_unknown_name(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.perception.matching.resources.get_ui_coordinates", lambda: SimpleNamespace(roi=SimpleNamespace())
    )

    with pytest.raises(ValueError, match="Invalid roi key: missing"):
        resolve_roi("missing")


def test_resolve_color_match_validates_inline_hsv_ranges() -> None:
    lower = np.array([0, 10, 20], dtype=np.uint8)
    upper = np.array([30, 200, 220], dtype=np.uint8)

    result = resolve_color_match([lower, upper])

    assert result is not None
    np.testing.assert_array_equal(result[0], lower)
    np.testing.assert_array_equal(result[1], upper)


def test_resolve_color_match_rejects_reversed_range() -> None:
    with pytest.raises(ValueError, match="Invalid color range"):
        resolve_color_match([np.array([30, 10, 20]), np.array([0, 20, 30])])


def test_process_template_refs_builds_a_template_from_an_image() -> None:
    image = np.full((4, 4, 4), 255, dtype=np.uint8)
    image[0, 0, 3] = 0

    templates = process_template_refs(image)

    assert len(templates) == 1
    assert isinstance(templates[0], Template)
    assert templates[0].alpha_mask is not None
    assert templates[0].alpha_mask[0, 0] == 0
