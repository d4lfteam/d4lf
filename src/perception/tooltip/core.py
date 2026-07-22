from copy import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.perception.image import crop
from src.perception.matching.engine import search
from src.perception.matching.models import SearchResult, TemplateMatch
from src.perception.roi import fit_roi_to_window_size, intersect
from src.perception.tooltip.texture import find_seperator_short
from src.settings import get_ui_coordinates

if TYPE_CHECKING:
    import numpy as np

ITEM_TOP_LEFT_THRESHOLD = 0.80
ITEM_BOTTOM_EDGE_THRESHOLD = 0.54

ITEM_TOP_LEFT_TEMPLATES = (
    "item_top_left_common",
    "item_top_left_legendary",
    "item_top_left_magic",
    "item_top_left_magic_1080p_special",
    "item_top_left_mythic",
    "item_top_left_rare",
    "item_top_left_set",
    "item_top_left_unique",
)


@dataclass(frozen=True)
class DescrDetection:
    """The production item-description detection result, including its template matches."""

    found: bool
    cropped_descr: np.ndarray | None = None
    crop_roi: list[int] | None = None
    top_left_match: TemplateMatch | None = None
    separator_match: TemplateMatch | None = None
    bottom_match: TemplateMatch | None = None
    failure_reason: str | None = None


def _choose_best_match(result: SearchResult, anchor_x: int) -> TemplateMatch | None:
    if not result.success or not result.matches:
        return None

    return min(result.matches, key=lambda candidate: (abs(candidate.center[0] - anchor_x), -candidate.score))


def _template_search(img: np.ndarray, anchor: int, roi: np.ndarray, take_debug_screenshot: bool = False):
    roi_copy = copy(roi)
    roi_copy[0] += anchor
    ok, roi_left = fit_roi_to_window_size(roi_copy, get_ui_coordinates().pos.window_dimensions)
    if ok:
        return search(
            ref=list(ITEM_TOP_LEFT_TEMPLATES),
            inp_img=img,
            roi=roi_left,
            threshold=ITEM_TOP_LEFT_THRESHOLD,
            mode="all",
            take_debug_screenshot=take_debug_screenshot,
        )
    return SearchResult(success=False)


def find_descr(img: np.ndarray, anchor: tuple[int, int]) -> tuple[bool, np.ndarray | None, list[int] | None]:
    detection = _find_descr_core(img, anchor, collect_diagnostics=False)
    return detection.found, detection.cropped_descr, detection.crop_roi


def find_descr_with_diagnostics(img: np.ndarray, anchor: tuple[int, int]) -> DescrDetection:
    """Find an item description and retain the template matches used to crop it."""
    return _find_descr_core(img, anchor, collect_diagnostics=True)


def get_separator_match_in_crop(detection: DescrDetection) -> TemplateMatch | None:
    """Translate a full-image separator match into the returned crop's coordinates."""
    if (
        detection.separator_match is None
        or detection.crop_roi is None
        or len(detection.crop_roi) != 4
        or detection.separator_match.center is None
        or detection.separator_match.region is None
    ):
        return None

    crop_x, crop_y, crop_width, crop_height = detection.crop_roi
    if (
        crop_x < 0
        or crop_y < 0
        or crop_width <= 0
        or crop_height <= 0
        or detection.cropped_descr is None
        or detection.cropped_descr.shape[:2] != (crop_height, crop_width)
    ):
        return None

    match = detection.separator_match
    region_x, region_y, region_width, region_height = match.region
    return TemplateMatch(
        center=(match.center[0] - crop_x, match.center[1] - crop_y),
        center_monitor=match.center_monitor,
        region=[region_x - crop_x, region_y - crop_y, region_width, region_height],
        region_monitor=match.region_monitor,
        name=match.name,
        score=match.score,
    )


def _find_descr_core(img: np.ndarray, anchor: tuple[int, int], *, collect_diagnostics: bool) -> DescrDetection:
    ui_coordinates = get_ui_coordinates()
    item_descr_width = ui_coordinates.offsets.item_descr_width
    item_descr_pad = ui_coordinates.offsets.item_descr_pad
    window_width, window_height = ui_coordinates.pos.window_dimensions

    if anchor[0] < window_width / 2:
        search_roi = ui_coordinates.roi.rel_descr_search_right
    else:
        search_roi = ui_coordinates.roi.rel_descr_search_left
    match = _choose_best_match(_template_search(img, anchor[0], search_roi), anchor[0])
    if match is not None:
        offset_top = int(window_height * 0.03)
        roi_y = match.region[1] + offset_top
        search_height = window_height - roi_y - offset_top
        delta_x = int(item_descr_width * 0.03)
        roi = [match.region[0] - delta_x, roi_y, item_descr_width + 2 * delta_x, search_height]

        separator_match = find_seperator_short(img, roi=roi, mode="first")

        if separator_match is not None:
            off_bottom_of_descr = get_ui_coordinates().offsets.item_descr_off_bottom_edge
            roi_height = get_ui_coordinates().pos.window_dimensions[1] - (2 * off_bottom_of_descr) - match.region[1]
            bottom_match = None
            if (
                res_bottom := search(
                    ref=["item_bottom_edge"],
                    inp_img=img,
                    roi=roi,
                    threshold=ITEM_BOTTOM_EDGE_THRESHOLD,
                    use_grayscale=True,
                    mode="all",
                )
            ).success:
                bottom_match = res_bottom.matches[0]
                roi_height = bottom_match.center[1] - off_bottom_of_descr - match.region[1]
            crop_roi = intersect(
                [
                    match.region[0] + item_descr_pad,
                    match.region[1] + item_descr_pad,
                    item_descr_width - 2 * item_descr_pad,
                    roi_height,
                ],
                (0, 0, img.shape[1], img.shape[0]),
            )
            if crop_roi is None:
                return DescrDetection(
                    found=False,
                    top_left_match=match if collect_diagnostics else None,
                    separator_match=separator_match if collect_diagnostics else None,
                    bottom_match=bottom_match if collect_diagnostics else None,
                    failure_reason="invalid_crop",
                )
            crop_roi = list(crop_roi)
            crop_roi_tuple = (crop_roi[0], crop_roi[1], crop_roi[2], crop_roi[3])
            cropped_descr = crop(img, crop_roi_tuple)
            return DescrDetection(
                found=True,
                cropped_descr=cropped_descr,
                crop_roi=crop_roi,
                top_left_match=match if collect_diagnostics else None,
                separator_match=separator_match if collect_diagnostics else None,
                bottom_match=bottom_match if collect_diagnostics else None,
            )

        return DescrDetection(
            found=False, top_left_match=match if collect_diagnostics else None, failure_reason="missing_separator"
        )

    return DescrDetection(found=False, failure_reason="missing_top_left_border")
