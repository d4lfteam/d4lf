import cv2

import src.template_finder
from src.utils.misc import is_in_roi


def test_search():
    """Test default search behavior (first match)."""
    image = cv2.imread("tests/assets/template_finder/stash_slots.png")
    slash = cv2.imread("tests/assets/template_finder/stash_slot_slash.png")
    cross = cv2.imread("tests/assets/template_finder/stash_slot_cross.png")
    threshold = 0.6
    result = src.template_finder.search([cross, slash], image, threshold)
    match = result.matches[0]
    assert threshold <= match.score < 1


def test_search_best_match():
    """Test search "best_match" behavior."""
    image = cv2.imread("tests/assets/template_finder/stash_slots.png")
    slash = cv2.imread("tests/assets/template_finder/stash_slot_slash.png")
    cross = cv2.imread("tests/assets/template_finder/stash_slot_cross.png")
    slash_expected_roi = [38, 0, 38, 38]
    result = src.template_finder.search([cross, slash], image, threshold=0.6, mode="all")
    match = result.matches[0]
    assert is_in_roi(slash_expected_roi, match.center)


def test_search_all():
    """Test all matches for a single template in argument."""
    image = cv2.imread("tests/assets/template_finder/stash_slots.png")
    empty = cv2.imread("tests/assets/template_finder/stash_slot_empty.png")
    result = src.template_finder.search(empty, image, threshold=0.98, mode="all")
    matches = result.matches
    assert len(matches) == 3


def test_search_all_multiple_templates():
    """Test all matches with multiple templates in argument."""
    image = cv2.imread("tests/assets/template_finder/stash_slots.png")
    empty = cv2.imread("tests/assets/template_finder/stash_slot_empty.png")
    slash = cv2.imread("tests/assets/template_finder/stash_slot_slash.png")
    result = src.template_finder.search([empty, slash], image, threshold=0.98, mode="all")
    matches = result.matches
    assert len(matches) == 4
