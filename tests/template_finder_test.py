from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import sleep

import cv2
import numpy as np

import src.template_finder
from src.config.data import Template
from src.utils.misc import is_in_roi


def test_search():
    """Test default search behavior (first match)."""
    image = cv2.imread("tests/assets/template_finder/stash_slots.png")
    slash = cv2.imread("tests/assets/template_finder/stash_slot_slash.png")
    cross = cv2.imread("tests/assets/template_finder/stash_slot_cross.png")
    threshold = 0.6
    result = src.template_finder.search([cross, slash], image, threshold)
    match = result.matches[0]
    assert threshold <= match.score <= 1


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


def test_search_all_stops_when_condition_is_met():
    """Test all matches can stop early once callers have enough matches."""
    image = cv2.imread("tests/assets/template_finder/stash_slots.png")
    empty = cv2.imread("tests/assets/template_finder/stash_slot_empty.png")

    result = src.template_finder.search(
        empty,
        image,
        threshold=0.98,
        mode="all",
        do_multi_process=False,
        stop_condition=lambda matches: len(matches) >= 2,
    )

    assert len(result.matches) == 2


def test_parallel_stop_condition_preserves_template_order(mocker):
    """A fast lower-priority template must not win a parallel early-stop search."""
    correct_template = Template(name="correct")
    false_template = Template(name="false")
    fast_template_finished = Event()

    mocker.patch("src.template_finder._process_template_refs", return_value=[correct_template, false_template])

    def fake_get_cv_result(template, *_args, **_kwargs):
        if template.name == "correct":
            assert fast_template_finished.wait(timeout=1)
            sleep(0.05)
        else:
            fast_template_finished.set()
        return np.array([[0.9]], dtype=np.float32), np.zeros((1, 1), dtype=np.uint8), [0, 0, 4, 4]

    mocker.patch("src.template_finder._get_cv_result", side_effect=fake_get_cv_result)
    executor = ThreadPoolExecutor(max_workers=2)
    mocker.patch("src.template_finder.TP", executor)

    try:
        result = src.template_finder.search(
            ref=["correct", "false"],
            inp_img=np.zeros((10, 10, 3), dtype=np.uint8),
            threshold=0.8,
            mode="all",
            stop_condition=lambda matches: len(matches) >= 1,
        )
    finally:
        executor.shutdown(wait=True)

    assert [match.name for match in result.matches] == ["correct"]
