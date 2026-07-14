import cv2
import numpy as np
import pytest

import src.template_finder
from src.utils.misc import is_in_roi


def _read_test_image(name: str) -> np.ndarray:
    image = cv2.imread(f"tests/assets/template_finder/{name}")
    if image is None:
        message = f"Missing test image: {name}"
        raise AssertionError(message)
    return image


def test_search():
    """Test default search behavior (first match)."""
    image = _read_test_image("stash_slots.png")
    slash = _read_test_image("stash_slot_slash.png")
    cross = _read_test_image("stash_slot_cross.png")
    threshold = 0.6
    result = src.template_finder.search([cross, slash], image, threshold)
    match = result.matches[0]
    assert threshold <= match.score < 1


def test_search_best_match():
    """Test search "best_match" behavior."""
    image = _read_test_image("stash_slots.png")
    slash = _read_test_image("stash_slot_slash.png")
    cross = _read_test_image("stash_slot_cross.png")
    slash_expected_roi = [38.0, 0.0, 38.0, 38.0]
    result = src.template_finder.search([cross, slash], image, threshold=0.6, mode="all")
    match = result.matches[0]
    assert match.center is not None
    assert is_in_roi(slash_expected_roi, match.center)


def test_search_all():
    """Test all matches for a single template in argument."""
    image = _read_test_image("stash_slots.png")
    empty = _read_test_image("stash_slot_empty.png")
    result = src.template_finder.search(empty, image, threshold=0.98, mode="all")
    matches = result.matches
    assert len(matches) == 3


def test_search_all_multiple_templates():
    """Test all matches with multiple templates in argument."""
    image = _read_test_image("stash_slots.png")
    empty = _read_test_image("stash_slot_empty.png")
    slash = _read_test_image("stash_slot_slash.png")
    result = src.template_finder.search([empty, slash], image, threshold=0.98, mode="all")
    matches = result.matches
    assert len(matches) == 4


def test_process_template_refs_preserves_transparent_template_mask():
    image = np.full((4, 4, 4), 255, dtype=np.uint8)
    image[0, 0, 3] = 0

    template = src.template_finder._process_template_refs(image)[0]

    assert isinstance(template.alpha_mask, np.ndarray)
    assert template.alpha_mask[0, 0] == 0
    assert template.alpha_mask[1, 1] == 255


def test_search_rejects_missing_named_roi(monkeypatch):
    image = _read_test_image("stash_slots.png")
    template = _read_test_image("stash_slot_cross.png")

    class EmptyRoi:
        pass

    class EmptyResources:
        roi = EmptyRoi()

    monkeypatch.setattr(src.template_finder, "ResManager", lambda: EmptyResources())

    with pytest.raises(ValueError, match="Invalid roi key: missing"):
        src.template_finder.search(template, image, threshold=0.6, roi="missing")
