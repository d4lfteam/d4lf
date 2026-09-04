"""Side-effect-free stages for evaluating a highlighted item."""

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

import numpy as np

from src.item import ASPECT_UPGRADES_LABEL, FilterResult
from src.perception import DescrDetection, LocatorResult

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from src.item import Affix, Item

Point = tuple[int, int]
ItemRoi = tuple[int, int, int, int]


@dataclass(frozen=True)
class TargetCenterSelection:
    """The slot center nearest to the current pointer position."""

    center: Point
    index: int
    distance: float


def select_target_center(
    mouse_position: Sequence[int | float] | np.ndarray,
    possible_centers: np.ndarray,
    possible_vendor_centers: np.ndarray,
    *,
    is_in_shop: bool,
) -> TargetCenterSelection:
    """Select the closest configured item center for an item tooltip."""
    centers = possible_vendor_centers if is_in_shop else possible_centers
    if len(centers) == 0:
        error_message = "at least one possible item center is required"
        raise ValueError(error_message)

    centers_array = np.asarray(centers)
    delta = centers_array - np.asarray(mouse_position)
    distances = np.linalg.norm(delta, axis=1)
    closest_index = int(np.argmin(distances))
    center_array = centers_array[closest_index]
    return TargetCenterSelection(
        center=(int(center_array[0]), int(center_array[1])),
        index=closest_index,
        distance=float(distances[closest_index]),
    )


def as_item_roi(crop_roi: list[int] | None) -> ItemRoi | None:
    """Convert a detector ROI to the tuple consumed by overlay requests."""
    if crop_roi is None or len(crop_roi) != 4:
        return None
    return (crop_roi[0], crop_roi[1], crop_roi[2], crop_roi[3])


class TooltipConfirmationStatus(StrEnum):
    """State of a tooltip after one or two frame observations."""

    ABSENT = "absent"
    INVALID = "invalid"
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"


@dataclass(frozen=True)
class TooltipConfirmation:
    """Typed result of stable-tooltip evaluation."""

    status: TooltipConfirmationStatus
    item_roi: ItemRoi | None
    top_left_corner: Point | None

    @property
    def confirmed(self) -> bool:
        """Whether the tooltip can be used for rendering."""
        return self.status is TooltipConfirmationStatus.CONFIRMED


def confirm_stable_tooltip(
    detection: DescrDetection,
    *,
    already_confirmed: bool,
    second_found: bool | None = None,
    second_cropped_descr: np.ndarray | None = None,
    histogram_score: float | None = None,
    minimum_score: float = 0.99,
) -> TooltipConfirmation:
    """Require a valid detector ROI and matching consecutive tooltip frames."""
    if not detection.found or detection.crop_roi is None or detection.cropped_descr is None:
        return TooltipConfirmation(TooltipConfirmationStatus.ABSENT, None, None)
    if len(detection.crop_roi) != 4:
        return TooltipConfirmation(TooltipConfirmationStatus.INVALID, None, None)
    item_roi = as_item_roi(detection.crop_roi)
    if item_roi is None:
        return TooltipConfirmation(TooltipConfirmationStatus.INVALID, None, None)

    top_left_corner = (item_roi[0], item_roi[1])
    if already_confirmed:
        return TooltipConfirmation(TooltipConfirmationStatus.CONFIRMED, item_roi, top_left_corner)

    is_stable = (
        second_found is True
        and second_cropped_descr is not None
        and histogram_score is not None
        and histogram_score >= minimum_score
    )
    status = TooltipConfirmationStatus.CONFIRMED if is_stable else TooltipConfirmationStatus.UNCONFIRMED
    return TooltipConfirmation(status, item_roi, top_left_corner)


class FilterOutcome(StrEnum):
    """Classification used to choose the next highlighting action."""

    STALE = "stale"
    SKIPPED = "skipped"
    NO_MATCH = "no_match"
    MATCH = "match"
    CODEX_UPGRADE = "codex_upgrade"


@dataclass(frozen=True)
class FilterEvaluation:
    """Filter result plus the information needed by marker and render stages."""

    outcome: FilterOutcome
    filter_result: FilterResult | None
    matched_affixes: tuple[Affix, ...] = ()
    aspect_matched: bool = False


def classify_filter_outcome(
    item_descr: Item, current_item: Item | None, filter_result: FilterResult
) -> FilterEvaluation:
    """Classify a filter result without queueing or otherwise mutating state."""
    if current_item is None or item_descr != current_item:
        return FilterEvaluation(FilterOutcome.STALE, None)
    if filter_result.skipped:
        return FilterEvaluation(FilterOutcome.SKIPPED, filter_result)

    matched_affixes = tuple(filter_result.matched[0].matched_affixes) if filter_result.matched else ()
    aspect_matched = any(matched.aspect_match for matched in filter_result.matched)
    if not filter_result.keep:
        return FilterEvaluation(FilterOutcome.NO_MATCH, filter_result, matched_affixes, aspect_matched)
    if any(matched.profile.endswith(ASPECT_UPGRADES_LABEL) for matched in filter_result.matched):
        return FilterEvaluation(FilterOutcome.CODEX_UPGRADE, filter_result, matched_affixes, aspect_matched)
    return FilterEvaluation(FilterOutcome.MATCH, filter_result, matched_affixes, aspect_matched)


@dataclass(frozen=True)
class EmptyOutlineCommand:
    """Queue an outline for an ignored item."""

    item: Item
    item_roi: ItemRoi
    color: str
    text: str | None


@dataclass(frozen=True)
class MatchCommand:
    """Queue a normal match outline and optional affix markers."""

    item: Item
    item_roi: ItemRoi
    filter_result: FilterResult
    locator_result: LocatorResult | None


@dataclass(frozen=True)
class NoMatchCommand:
    """Queue an outline for an item that did not match a filter."""

    item: Item
    item_roi: ItemRoi


@dataclass(frozen=True)
class CodexUpgradeCommand:
    """Queue the special codex-upgrade outline."""

    item: Item
    item_roi: ItemRoi
    filter_result: FilterResult


RenderingCommand = EmptyOutlineCommand | MatchCommand | NoMatchCommand | CodexUpgradeCommand


def select_rendering_command(
    item: Item,
    item_roi: ItemRoi,
    *,
    ignored_item: bool,
    ignored_color: str = "",
    sanctified: bool,
    filter_evaluation: FilterEvaluation | None,
    locator_result: LocatorResult | None = None,
) -> RenderingCommand | None:
    """Select a queue command from classified item state."""
    if ignored_item:
        text = "Sanctified (Not Supported)" if sanctified else None
        return EmptyOutlineCommand(item, item_roi, ignored_color, text)
    if filter_evaluation is None:
        return None
    if filter_evaluation.outcome is FilterOutcome.CODEX_UPGRADE:
        if filter_evaluation.filter_result is None:
            return None
        return CodexUpgradeCommand(item, item_roi, filter_evaluation.filter_result)
    if filter_evaluation.outcome is FilterOutcome.MATCH:
        if filter_evaluation.filter_result is None:
            return None
        return MatchCommand(item, item_roi, filter_evaluation.filter_result, locator_result)
    if filter_evaluation.outcome is FilterOutcome.NO_MATCH:
        return NoMatchCommand(item, item_roi)
    return None


@dataclass(frozen=True)
class MarkerLocationResult:
    """Marker result and any valid ROI found during a retry."""

    locator_result: LocatorResult
    item_roi: ItemRoi | None
    retried: bool


def locate_markers_with_retry(
    detection: DescrDetection,
    *,
    locate: Callable[[DescrDetection], LocatorResult],
    retry_detection: DescrDetection | None = None,
    initial_result: LocatorResult | None = None,
) -> MarkerLocationResult:
    """Locate markers, optionally replacing an unreliable result with a retry."""
    result = initial_result
    if result is None:
        result = locate(detection) if detection.cropped_descr is not None else LocatorResult([], reliable=False)
    item_roi = as_item_roi(detection.crop_roi)
    if result.reliable or retry_detection is None or not retry_detection.found:
        return MarkerLocationResult(locator_result=result, item_roi=item_roi, retried=False)

    retry_result = (
        locate(retry_detection) if retry_detection.cropped_descr is not None else LocatorResult([], reliable=False)
    )
    retry_roi = as_item_roi(retry_detection.crop_roi)
    return MarkerLocationResult(
        locator_result=retry_result, item_roi=retry_roi if retry_roi is not None else item_roi, retried=True
    )
