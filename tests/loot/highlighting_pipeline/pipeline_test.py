import numpy as np
import pytest

from src.item import FilterResult, Item, MatchedFilter
from src.loot.highlighting_pipeline import (
    CodexUpgradeCommand,
    EmptyOutlineCommand,
    FilterOutcome,
    MatchCommand,
    NoMatchCommand,
    TooltipConfirmationStatus,
    as_item_roi,
    classify_filter_outcome,
    confirm_stable_tooltip,
    locate_markers_with_retry,
    select_rendering_command,
    select_target_center,
)
from src.perception import DescrDetection, LocatorResult


def test_select_target_center_uses_vendor_centers_for_shop_items() -> None:
    result = select_target_center(
        (98, 101), np.array([[0, 0], [50, 50]]), np.array([[100, 100], [200, 200]]), is_in_shop=True
    )

    assert result.center == (100, 100)
    assert result.index == 0
    assert result.distance == pytest.approx(2.2360679775)


def test_select_target_center_rejects_empty_centers() -> None:
    with pytest.raises(ValueError, match="possible item center"):
        select_target_center((0, 0), np.empty((0, 2)), np.empty((0, 2)), is_in_shop=False)


@pytest.mark.parametrize(("crop_roi", "expected"), [([1, 2, 3, 4], (1, 2, 3, 4)), (None, None), ([1, 2, 3], None)])
def test_as_item_roi_converts_only_four_element_rois(crop_roi, expected) -> None:
    assert as_item_roi(crop_roi) == expected


def test_confirm_stable_tooltip_requires_a_matching_second_frame() -> None:
    detection = DescrDetection(found=True, cropped_descr=np.zeros((2, 2)), crop_roi=[1, 2, 3, 4])

    result = confirm_stable_tooltip(
        detection,
        already_confirmed=False,
        second_found=True,
        second_cropped_descr=np.ones((2, 2)),
        histogram_score=0.98,
    )

    assert result.status is TooltipConfirmationStatus.UNCONFIRMED
    assert result.item_roi == (1, 2, 3, 4)

    confirmed = confirm_stable_tooltip(
        detection,
        already_confirmed=False,
        second_found=True,
        second_cropped_descr=np.ones((2, 2)),
        histogram_score=0.99,
    )
    assert confirmed.status is TooltipConfirmationStatus.CONFIRMED
    assert confirmed.top_left_corner == (1, 2)


@pytest.mark.parametrize(
    ("detection", "expected_status"),
    [
        (DescrDetection(found=False), TooltipConfirmationStatus.ABSENT),
        (
            DescrDetection(found=True, cropped_descr=np.zeros((1, 1)), crop_roi=[1, 2, 3]),
            TooltipConfirmationStatus.INVALID,
        ),
    ],
)
def test_confirm_stable_tooltip_classifies_unusable_detections(detection, expected_status) -> None:
    assert confirm_stable_tooltip(detection, already_confirmed=False).status is expected_status


def test_classify_filter_outcome_keeps_only_the_current_item() -> None:
    item = Item(name="helm")
    result = FilterResult(True, [MatchedFilter("profile")])

    stale = classify_filter_outcome(item, Item(name="different"), result)
    current = classify_filter_outcome(item, item, result)

    assert stale.outcome is FilterOutcome.STALE
    assert stale.filter_result is None
    assert current.outcome is FilterOutcome.MATCH
    assert current.filter_result is result


@pytest.mark.parametrize(
    ("filter_result", "expected_outcome"),
    [
        (FilterResult(False, [], skipped=True), FilterOutcome.SKIPPED),
        (FilterResult(False, [MatchedFilter("profile")]), FilterOutcome.NO_MATCH),
        (FilterResult(True, [MatchedFilter("profile.AspectUpgrades")]), FilterOutcome.CODEX_UPGRADE),
    ],
)
def test_classify_filter_outcome_distinguishes_rendering_paths(filter_result, expected_outcome) -> None:
    item = Item(name="helm")

    assert classify_filter_outcome(item, item, filter_result).outcome is expected_outcome


def test_select_rendering_command_builds_ignored_sanctified_command() -> None:
    item = Item(name="helm")

    command = select_rendering_command(
        item, (1, 2, 3, 4), ignored_item=True, ignored_color="blue", sanctified=True, filter_evaluation=None
    )

    assert command == EmptyOutlineCommand(item, (1, 2, 3, 4), "blue", "Sanctified (Not Supported)")


def test_select_rendering_command_builds_each_filter_command() -> None:
    item = Item(name="helm")
    roi = (1, 2, 3, 4)
    locator = LocatorResult(markers=[], reliable=True)
    cases = [
        (FilterResult(True, [MatchedFilter("profile")]), MatchCommand),
        (FilterResult(False, [MatchedFilter("profile")]), NoMatchCommand),
        (FilterResult(True, [MatchedFilter("profile.AspectUpgrades")]), CodexUpgradeCommand),
    ]

    for filter_result, command_type in cases:
        evaluation = classify_filter_outcome(item, item, filter_result)
        command = select_rendering_command(
            item,
            roi,
            ignored_item=False,
            ignored_color="blue",
            sanctified=False,
            filter_evaluation=evaluation,
            locator_result=locator,
        )
        assert isinstance(command, command_type)


def test_select_rendering_command_does_not_render_skipped_or_stale_items() -> None:
    item = Item(name="helm")
    for filter_result, current_item in [
        (FilterResult(False, [], skipped=True), item),
        (FilterResult(True, [MatchedFilter("profile")]), Item(name="different")),
    ]:
        evaluation = classify_filter_outcome(item, current_item, filter_result)
        assert (
            select_rendering_command(
                item,
                (1, 2, 3, 4),
                ignored_item=False,
                ignored_color="blue",
                sanctified=False,
                filter_evaluation=evaluation,
            )
            is None
        )


def test_locate_markers_with_retry_replaces_unreliable_result_and_roi() -> None:
    first = DescrDetection(found=True, cropped_descr=np.zeros((1, 1)), crop_roi=[1, 2, 3, 4])
    retry = DescrDetection(found=True, cropped_descr=np.ones((1, 1)), crop_roi=[5, 6, 7, 8])
    initial_result = LocatorResult(markers=[], reliable=False)
    retry_result = LocatorResult(markers=[], reliable=True)
    calls: list[DescrDetection] = []

    def locate(detection: DescrDetection) -> LocatorResult:
        calls.append(detection)
        return retry_result

    result = locate_markers_with_retry(first, locate=locate, retry_detection=retry, initial_result=initial_result)

    assert result.locator_result is retry_result
    assert result.item_roi == (5, 6, 7, 8)
    assert result.retried is True
    assert calls == [retry]


def test_locate_markers_with_retry_does_not_retry_reliable_result() -> None:
    detection = DescrDetection(found=True, cropped_descr=np.zeros((1, 1)), crop_roi=[1, 2, 3, 4])
    result = LocatorResult(markers=[], reliable=True)
    calls = 0

    def locate(_: DescrDetection) -> LocatorResult:
        nonlocal calls
        calls += 1
        return result

    located = locate_markers_with_retry(detection, locate=locate, retry_detection=detection)

    assert located.locator_result is result
    assert located.retried is False
    assert calls == 1
