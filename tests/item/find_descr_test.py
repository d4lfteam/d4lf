from types import SimpleNamespace

import numpy as np

from src.item.data.rarity import ItemRarity
from src.item.find_descr import (
    DescrDetection,
    _choose_best_result,
    _find_descr_core,
    find_descr,
    find_descr_with_diagnostics,
    get_separator_match_in_crop,
)
from src.template_finder import SearchResult, TemplateMatch


def test_choose_best_result_on_left_half_selects_closest_match_to_right():
    closest_from_left_result = TemplateMatch(center=(90, 70), score=0.99)
    closest_from_right_result = TemplateMatch(center=(125, 60), score=0.70)

    result = _choose_best_result(
        SearchResult(success=True, matches=[closest_from_left_result]),
        SearchResult(success=True, matches=[closest_from_right_result]),
        anchor_x=120,
        screen_width=400,
    )

    assert result.success
    assert result.matches == [closest_from_right_result]


def test_choose_best_result_on_right_half_selects_closest_match_to_left():
    closest_from_left_result = TemplateMatch(center=(275, 70), score=0.70)
    closest_from_right_result = TemplateMatch(center=(310, 60), score=0.99)

    result = _choose_best_result(
        SearchResult(success=True, matches=[closest_from_left_result]),
        SearchResult(success=True, matches=[closest_from_right_result]),
        anchor_x=300,
        screen_width=400,
    )

    assert result.success
    assert result.matches == [closest_from_left_result]


def test_choose_best_result_returns_no_result_when_preferred_side_is_empty():
    only_match = TemplateMatch(center=(90, 70), score=0.70)

    result = _choose_best_result(
        SearchResult(success=True, matches=[only_match]), SearchResult(success=False), anchor_x=120, screen_width=400
    )

    assert not result.success


def test_find_descr_uses_shared_core_without_diagnostics(mocker):
    detection = DescrDetection(found=True, rarity=ItemRarity.Legendary, crop_roi=[1, 2, 3, 4])
    core = mocker.patch("src.item.find_descr._find_descr_core", return_value=detection)
    image = object()

    result = find_descr(image, (100, 200))

    assert result == (True, ItemRarity.Legendary, None, [1, 2, 3, 4])
    core.assert_called_once_with(image, (100, 200), collect_diagnostics=False)


def test_find_descr_with_diagnostics_uses_shared_core_with_diagnostics(mocker):
    detection = DescrDetection(found=False, failure_reason="missing_separator")
    core = mocker.patch("src.item.find_descr._find_descr_core", return_value=detection)
    image = object()

    result = find_descr_with_diagnostics(image, (100, 200))

    assert result is detection
    core.assert_called_once_with(image, (100, 200), collect_diagnostics=True)


def test_get_separator_match_in_crop_translates_full_image_coordinates():
    detection = DescrDetection(
        found=True,
        cropped_descr=np.zeros((100, 100, 3), dtype=np.uint8),
        crop_roi=[90, 200, 100, 100],
        separator_match=TemplateMatch(
            center=(110, 220), region=[100, 210, 20, 10], name="item_seperator_short_rare", score=0.9
        ),
    )

    result = get_separator_match_in_crop(detection)

    assert result is not detection.separator_match
    assert result.center == (20, 20)
    assert result.region == [10, 10, 20, 10]
    assert result.name == detection.separator_match.name
    assert result.score == detection.separator_match.score


def test_get_separator_match_in_crop_returns_none_for_invalid_crop():
    detection = DescrDetection(
        found=True,
        cropped_descr=object(),
        crop_roi=[-1, 200, 100, 100],
        separator_match=TemplateMatch(
            center=(10, 220), region=[0, 210, 20, 10], name="item_seperator_short_rare", score=0.9
        ),
    )

    assert get_separator_match_in_crop(detection) is None


def test_find_descr_clips_crop_to_image_before_translating_separator(mocker):
    mocker.patch(
        "src.item.find_descr.ResManager",
        return_value=SimpleNamespace(
            offsets=SimpleNamespace(item_descr_width=100, item_descr_pad=10, item_descr_off_bottom_edge=0),
            pos=SimpleNamespace(window_dimensions=(100, 100)),
            roi=SimpleNamespace(rel_descr_search_left=[0, 0, 1, 1], rel_descr_search_right=[0, 0, 1, 1]),
        ),
    )
    rarity_match = TemplateMatch(center=(80, 10), region=[70, 0, 20, 20], name="item_leg_top_left", score=0.9)
    separator_match = TemplateMatch(center=(85, 30), region=[80, 25, 10, 10], name="separator", score=0.9)
    mocker.patch(
        "src.item.find_descr._template_search",
        side_effect=[SearchResult(success=True, matches=[rarity_match]), SearchResult()],
    )
    mocker.patch("src.item.find_descr.find_seperator_short", return_value=separator_match)
    mocker.patch("src.item.find_descr.search", return_value=SearchResult())

    detection = _find_descr_core(np.zeros((100, 100, 3), dtype=np.uint8), (0, 0), collect_diagnostics=True)

    assert detection.crop_roi == [80, 10, 20, 90]
    assert detection.cropped_descr.shape[:2] == (90, 20)
    assert get_separator_match_in_crop(detection).center == (5, 20)
