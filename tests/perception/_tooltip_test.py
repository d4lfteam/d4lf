from types import SimpleNamespace

import numpy as np

from src.perception._matching_models import SearchResult, TemplateMatch
from src.perception._tooltip import (
    DescrDetection,
    _choose_best_result,
    _find_descr_core,
    find_descr,
    find_descr_with_diagnostics,
    get_separator_match_in_crop,
)


def _make_match(
    center: tuple[int, int], score: float, name: str = "", region: list[int] | None = None
) -> TemplateMatch:
    resolved_region = region if region is not None else [center[0], center[1], 1, 1]
    return TemplateMatch(
        center=center,
        center_monitor=center,
        name=name,
        region=resolved_region,
        region_monitor=resolved_region.copy(),
        score=score,
    )


def test_find_descr_ignores_successful_search_without_matches(monkeypatch):
    resources = SimpleNamespace(
        offsets=SimpleNamespace(item_descr_width=100, item_descr_pad=10),
        pos=SimpleNamespace(window_dimensions=(3840, 2160)),
        roi=SimpleNamespace(
            rel_descr_search_left=np.array([0, 0, 10, 10]), rel_descr_search_right=np.array([0, 0, 10, 10])
        ),
    )
    search_results = iter([SearchResult(success=True), SearchResult()])
    monkeypatch.setattr("src.perception._tooltip.get_ui_coordinates", lambda: resources)
    monkeypatch.setattr("src.perception._tooltip._template_search", lambda *_args, **_kwargs: next(search_results))

    assert find_descr(np.zeros((20, 20, 3), dtype=np.uint8), (0, 0)) == (False, None, None)


def test_choose_best_result_on_left_half_selects_closest_match_to_right():
    closest_from_left_result = _make_match((90, 70), 0.99)
    closest_from_right_result = _make_match((125, 60), 0.70)

    result = _choose_best_result(
        SearchResult(success=True, matches=[closest_from_left_result]),
        SearchResult(success=True, matches=[closest_from_right_result]),
        anchor_x=120,
        screen_width=400,
    )

    assert result.success
    assert result.matches == [closest_from_right_result]


def test_choose_best_result_on_right_half_selects_closest_match_to_left():
    closest_from_left_result = _make_match((275, 70), 0.70)
    closest_from_right_result = _make_match((310, 60), 0.99)

    result = _choose_best_result(
        SearchResult(success=True, matches=[closest_from_left_result]),
        SearchResult(success=True, matches=[closest_from_right_result]),
        anchor_x=300,
        screen_width=400,
    )

    assert result.success
    assert result.matches == [closest_from_left_result]


def test_choose_best_result_returns_no_result_when_preferred_side_is_empty():
    only_match = _make_match((90, 70), 0.70)

    result = _choose_best_result(
        SearchResult(success=True, matches=[only_match]), SearchResult(success=False), anchor_x=120, screen_width=400
    )

    assert not result.success


def test_find_descr_uses_shared_core_without_diagnostics(mocker):
    detection = DescrDetection(found=True, crop_roi=[1, 2, 3, 4])
    core = mocker.patch("src.perception._tooltip._find_descr_core", return_value=detection)
    image = np.zeros((10, 10, 3), dtype=np.uint8)

    result = find_descr(image, (100, 200))

    assert result == (True, None, [1, 2, 3, 4])
    core.assert_called_once_with(image, (100, 200), collect_diagnostics=False)


def test_find_descr_with_diagnostics_uses_shared_core_with_diagnostics(mocker):
    detection = DescrDetection(found=False, failure_reason="missing_separator")
    core = mocker.patch("src.perception._tooltip._find_descr_core", return_value=detection)
    image = np.zeros((10, 10, 3), dtype=np.uint8)

    result = find_descr_with_diagnostics(image, (100, 200))

    assert result is detection
    core.assert_called_once_with(image, (100, 200), collect_diagnostics=True)


def test_get_separator_match_in_crop_translates_full_image_coordinates():
    detection = DescrDetection(
        found=True,
        cropped_descr=np.zeros((100, 100, 3), dtype=np.uint8),
        crop_roi=[90, 200, 100, 100],
        separator_match=_make_match((110, 220), 0.9, name="item_seperator_short_rare", region=[100, 210, 20, 10]),
    )

    result = get_separator_match_in_crop(detection)

    assert result is not detection.separator_match
    assert result is not None
    separator_match = detection.separator_match
    assert separator_match is not None
    assert result.center == (20, 20)
    assert result.region == [10, 10, 20, 10]
    assert result.name == separator_match.name
    assert result.score == separator_match.score


def test_get_separator_match_in_crop_returns_none_for_invalid_crop():
    detection = DescrDetection(
        found=True,
        cropped_descr=None,
        crop_roi=[-1, 200, 100, 100],
        separator_match=_make_match((10, 220), 0.9, name="item_seperator_short_rare", region=[0, 210, 20, 10]),
    )

    assert get_separator_match_in_crop(detection) is None


def test_find_descr_clips_crop_to_image_before_translating_separator(mocker):
    mocker.patch(
        "src.perception._tooltip.get_ui_coordinates",
        return_value=SimpleNamespace(
            offsets=SimpleNamespace(item_descr_width=100, item_descr_pad=10, item_descr_off_bottom_edge=0),
            pos=SimpleNamespace(window_dimensions=(100, 100)),
            roi=SimpleNamespace(rel_descr_search_left=[0, 0, 1, 1], rel_descr_search_right=[0, 0, 1, 1]),
        ),
    )
    top_left_match = _make_match((80, 10), 0.9, name="item_top_left_legendary", region=[70, 0, 20, 20])
    separator_match = _make_match((85, 30), 0.9, name="separator", region=[80, 25, 10, 10])
    mocker.patch(
        "src.perception._tooltip._template_search",
        side_effect=[SearchResult(success=True, matches=[top_left_match]), SearchResult()],
    )
    mocker.patch("src.perception._tooltip.find_seperator_short", return_value=separator_match)
    mocker.patch("src.perception._tooltip.search", return_value=SearchResult())

    detection = _find_descr_core(np.zeros((100, 100, 3), dtype=np.uint8), (0, 0), collect_diagnostics=True)

    assert detection.crop_roi == [80, 10, 20, 90]
    assert detection.cropped_descr is not None
    assert detection.cropped_descr.shape[:2] == (90, 20)
    translated_match = get_separator_match_in_crop(detection)
    assert translated_match is not None
    assert translated_match.center == (5, 20)
