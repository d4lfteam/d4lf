from copy import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.config.ui import ResManager
from src.item.data.rarity import ItemRarity
from src.item.descr.texture import find_seperator_short
from src.template_finder import SearchResult, TemplateMatch, search
from src.utils.image_operations import crop
from src.utils.roi_operations import fit_roi_to_window_size, intersect

if TYPE_CHECKING:
    import numpy as np

ITEM_TOP_LEFT_THRESHOLD = 0.85
ITEM_BOTTOM_EDGE_THRESHOLD = 0.54

map_template_rarity = {
    "item_top_left_common": ItemRarity.Common,
    "item_top_left_legendary": ItemRarity.Legendary,
    "item_top_left_magic": ItemRarity.Magic,
    "item_top_left_mythic": ItemRarity.Mythic,
    "item_top_left_rare": ItemRarity.Rare,
    "item_top_left_unique": ItemRarity.Unique,
}


@dataclass(frozen=True)
class DescrDetection:
    """The production item-description detection result, including its template matches."""

    found: bool
    rarity: ItemRarity | None = None
    cropped_descr: np.ndarray | None = None
    crop_roi: list[int] | None = None
    rarity_match: TemplateMatch | None = None
    separator_match: TemplateMatch | None = None
    bottom_match: TemplateMatch | None = None
    failure_reason: str | None = None


def _choose_best_result(
    res_left: SearchResult, res_right: SearchResult, anchor_x: int, screen_width: int
) -> SearchResult:
    candidates = [match for result in (res_left, res_right) if result.success for match in result.matches]
    if not candidates:
        return SearchResult(success=False)

    if anchor_x < screen_width / 2:
        preferred_candidates = [candidate for candidate in candidates if candidate.center[0] > anchor_x]
    else:
        preferred_candidates = [candidate for candidate in candidates if candidate.center[0] < anchor_x]
    if not preferred_candidates:
        return SearchResult(success=False)

    match = min(preferred_candidates, key=lambda candidate: (abs(candidate.center[0] - anchor_x), -candidate.score))
    return SearchResult(success=True, matches=[match])


def _template_search(img: np.ndarray, anchor: int, roi: np.ndarray, take_debug_screenshot: bool = False):
    roi_copy = copy(roi)
    roi_copy[0] += anchor
    ok, roi_left = fit_roi_to_window_size(roi_copy, ResManager().pos.window_dimensions)
    if ok:
        return search(
            ref=list(map_template_rarity.keys()),
            inp_img=img,
            roi=roi_left,
            threshold=ITEM_TOP_LEFT_THRESHOLD,
            mode="all",
            take_debug_screenshot=take_debug_screenshot,
        )
    return SearchResult(success=False)


def find_descr(
    img: np.ndarray, anchor: tuple[int, int]
) -> tuple[bool, ItemRarity | None, np.ndarray | None, list[int] | None]:
    detection = _find_descr_core(img, anchor, collect_diagnostics=False)
    return detection.found, detection.rarity, detection.cropped_descr, detection.crop_roi


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
    item_descr_width = ResManager().offsets.item_descr_width
    item_descr_pad = ResManager().offsets.item_descr_pad
    window_width, window_height = ResManager().pos.window_dimensions

    res_left = _template_search(img, anchor[0], ResManager().roi.rel_descr_search_left)
    res_right = _template_search(img, anchor[0], ResManager().roi.rel_descr_search_right)

    res = _choose_best_result(res_left, res_right, anchor[0], window_width)

    if res.success and res.matches:
        match = res.matches[0]
        rarity = map_template_rarity[match.name.lower()]
        # find equipe template
        offset_top = int(window_height * 0.03)
        roi_y = match.region[1] + offset_top
        search_height = window_height - roi_y - offset_top
        delta_x = int(item_descr_width * 0.03)
        roi = [match.region[0] - delta_x, roi_y, item_descr_width + 2 * delta_x, search_height]

        separator_match = find_seperator_short(img, roi=roi, mode="first")

        if separator_match is not None:
            off_bottom_of_descr = ResManager().offsets.item_descr_off_bottom_edge
            roi_height = ResManager().pos.window_dimensions[1] - (2 * off_bottom_of_descr) - match.region[1]
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
                    rarity=rarity,
                    rarity_match=match if collect_diagnostics else None,
                    separator_match=separator_match if collect_diagnostics else None,
                    bottom_match=bottom_match if collect_diagnostics else None,
                    failure_reason="invalid_crop",
                )
            crop_roi = list(crop_roi)
            crop_roi_tuple = (crop_roi[0], crop_roi[1], crop_roi[2], crop_roi[3])
            cropped_descr = crop(img, crop_roi_tuple)
            return DescrDetection(
                found=True,
                rarity=rarity,
                cropped_descr=cropped_descr,
                crop_roi=crop_roi,
                rarity_match=match if collect_diagnostics else None,
                separator_match=separator_match if collect_diagnostics else None,
                bottom_match=bottom_match if collect_diagnostics else None,
            )

        return DescrDetection(
            found=False, rarity_match=match if collect_diagnostics else None, failure_reason="missing_separator"
        )

    return DescrDetection(found=False, failure_reason="missing_rarity_border")
