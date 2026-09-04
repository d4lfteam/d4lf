from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import sleep

import cv2
import numpy as np
import pytest

import src.perception.matching.engine as matching
from src.perception.roi import is_point_in_roi
from src.settings import Template


def _read_test_image(name: str) -> np.ndarray:
    image = cv2.imread(f"tests/assets/template_finder/{name}")
    if image is None:
        message = f"Missing test image: {name}"
        raise AssertionError(message)
    return image


def test_search() -> None:
    """Test default search behavior (first match)."""
    image = _read_test_image("stash_slots.png")
    slash = _read_test_image("stash_slot_slash.png")
    cross = _read_test_image("stash_slot_cross.png")
    threshold = 0.6
    result = matching.search([cross, slash], image, threshold)
    match = result.matches[0]
    assert threshold <= match.score <= 1


def test_search_best_match() -> None:
    """Test search "best_match" behavior."""
    image = _read_test_image("stash_slots.png")
    slash = _read_test_image("stash_slot_slash.png")
    cross = _read_test_image("stash_slot_cross.png")
    slash_expected_roi = [38.0, 0.0, 38.0, 38.0]
    result = matching.search([cross, slash], image, threshold=0.6, mode="all")
    match = result.matches[0]
    assert match.center is not None
    assert is_point_in_roi(slash_expected_roi, match.center)


def test_search_all() -> None:
    """Test all matches for a single template in argument."""
    image = _read_test_image("stash_slots.png")
    empty = _read_test_image("stash_slot_empty.png")
    result = matching.search(empty, image, threshold=0.98, mode="all")
    matches = result.matches
    assert len(matches) == 3


def test_search_all_multiple_templates() -> None:
    """Test all matches with multiple templates in argument."""
    image = _read_test_image("stash_slots.png")
    empty = _read_test_image("stash_slot_empty.png")
    slash = _read_test_image("stash_slot_slash.png")
    result = matching.search([empty, slash], image, threshold=0.98, mode="all")
    matches = result.matches
    assert len(matches) == 4


def test_search_all_stops_when_condition_is_met() -> None:
    """Test all matches can stop early once callers have enough matches."""
    image = _read_test_image("stash_slots.png")
    empty = _read_test_image("stash_slot_empty.png")

    result = matching.search(
        empty, image, threshold=0.98, mode="all", use_parallel=False, stop_condition=lambda matches: len(matches) >= 2
    )

    assert len(result.matches) == 2


@pytest.mark.parametrize("mode", ["all", "first"])
def test_parallel_stop_condition_preserves_template_order(mocker, mode: str) -> None:
    """A fast lower-priority template must not win a parallel early-stop search."""
    correct_template = Template(name="correct")
    false_template = Template(name="false")
    fast_template_finished = Event()

    mocker.patch(
        "src.perception.matching.engine._process_template_refs", return_value=[correct_template, false_template]
    )

    def fake_get_cv_result(template, *_args, **_kwargs):
        if template.name == "correct":
            assert fast_template_finished.wait(timeout=1)
            sleep(0.05)
        else:
            fast_template_finished.set()
        return np.array([[0.9]], dtype=np.float32), np.zeros((1, 1), dtype=np.uint8), [0, 0, 4, 4]

    mocker.patch("src.perception.matching.engine._get_cv_result", side_effect=fake_get_cv_result)
    executor = ThreadPoolExecutor(max_workers=2)

    try:
        result = matching.search(
            ref=["correct", "false"],
            inp_img=np.zeros((10, 10, 3), dtype=np.uint8),
            threshold=0.8,
            mode=mode,
            stop_condition=lambda matches: len(matches) >= 1,
            _executor=executor,
        )
    finally:
        executor.shutdown(wait=True)

    assert [match.name for match in result.matches] == ["correct"]


def test_parallel_polling_reuses_one_owned_executor(mocker) -> None:
    templates = [Template(name="first"), Template(name="second")]
    mocker.patch("src.perception.matching.engine._process_template_refs", return_value=templates)
    mocker.patch("src.perception.matching.engine._find_template_matches", return_value=[])
    executor_type = mocker.patch("src.perception.matching.engine.ThreadPoolExecutor", wraps=ThreadPoolExecutor)
    clock = iter((0.0, 0.0, 0.5, 1.0))
    mocker.patch("src.perception.matching.engine.time.monotonic", side_effect=clock)

    result = matching.search(ref=["first", "second"], inp_img=np.zeros((2, 2, 3), dtype=np.uint8), timeout=1)

    assert not result.success
    assert executor_type.call_count == 1


def test_process_template_refs_preserves_transparent_template_mask() -> None:
    image = np.full((4, 4, 4), 255, dtype=np.uint8)
    image[0, 0, 3] = 0

    template = matching._process_template_refs(image)[0]

    assert isinstance(template.alpha_mask, np.ndarray)
    assert template.alpha_mask[0, 0] == 0
    assert template.alpha_mask[1, 1] == 255


def test_search_rejects_missing_named_roi(monkeypatch) -> None:
    image = _read_test_image("stash_slots.png")
    template = _read_test_image("stash_slot_cross.png")

    class EmptyRoi:
        pass

    class EmptyResources:
        roi = EmptyRoi()

    monkeypatch.setattr("src.perception.matching.resources.get_ui_coordinates", lambda: EmptyResources())

    with pytest.raises(ValueError, match="Invalid roi key: missing"):
        matching.search(template, image, threshold=0.6, roi="missing")
