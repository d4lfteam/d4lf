from copy import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.config.ui import ResManager
from src.item.data.rarity import ItemRarity
from src.item.descr.texture import find_seperator_short
from src.template_finder import SearchResult, TemplateMatch, search
from src.utils.image_operations import crop
from src.utils.roi_operations import fit_roi_to_window_size

if TYPE_CHECKING:
    import numpy as np

map_template_rarity = {
    "item_common_top_left": ItemRarity.Common,
    "item_leg_top_left": ItemRarity.Legendary,
    "item_magic_top_left": ItemRarity.Magic,
    "item_mythic_top_left": ItemRarity.Mythic,
    "item_rare_top_left": ItemRarity.Rare,
    "item_unique_top_left": ItemRarity.Unique,
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


def _choose_best_result(res_left: SearchResult, res_right: SearchResult) -> SearchResult:
    if res_left.success and not res_right.success:
        return res_left
    if res_right.success and not res_left.success:
        return res_right
    if res_left.success and res_right.success:
        return res_left if res_left.matches[0].score > res_right.matches[0].score else res_right
    return SearchResult(success=False)


def _template_search(img: np.ndarray, anchor: int, roi: np.ndarray, take_debug_screenshot: bool = False):
    roi_copy = copy(roi)
    roi_copy[0] += anchor
    ok, roi_left = fit_roi_to_window_size(roi_copy, ResManager().pos.window_dimensions)
    if ok:
        return search(
            ref=list(map_template_rarity.keys()),
            inp_img=img,
            roi=roi_left,
            threshold=0.8,
            mode="all",
            take_debug_screenshot=take_debug_screenshot,
        )
    return SearchResult(success=False)


def find_descr(
    img: np.ndarray, anchor: tuple[int, int]
) -> tuple[bool, ItemRarity, np.ndarray, tuple[int, int, int, int]]:
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
        region=[region_x - crop_x, region_y - crop_y, region_width, region_height],
        name=match.name,
        score=match.score,
    )


def _find_descr_core(img: np.ndarray, anchor: tuple[int, int], *, collect_diagnostics: bool) -> DescrDetection:
    item_descr_width = ResManager().offsets.item_descr_width
    item_descr_pad = ResManager().offsets.item_descr_pad
    _, window_height = ResManager().pos.window_dimensions

    res_left = _template_search(img, anchor[0], ResManager().roi.rel_descr_search_left)
    res_right = _template_search(img, anchor[0], ResManager().roi.rel_descr_search_right)

    res = _choose_best_result(res_left, res_right)

    if res is not None and res.success:
        match = res.matches[0]
        rarity = map_template_rarity[match.name.lower()]
        # find equipe template
        offset_top = int(window_height * 0.03)
        roi_y = match.region[1] + offset_top
        search_height = window_height - roi_y - offset_top
        delta_x = int(item_descr_width * 0.03)
        roi = [match.region[0] - delta_x, roi_y, item_descr_width + 2 * delta_x, search_height]

        separator_match = find_seperator_short(img, threshold=0.8, roi=roi, mode="first")

        if separator_match is not None:
            off_bottom_of_descr = ResManager().offsets.item_descr_off_bottom_edge
            roi_height = ResManager().pos.window_dimensions[1] - (2 * off_bottom_of_descr) - match.region[1]
            bottom_match = None
            if (
                res_bottom := search(
                    ref=["item_bottom_edge"], inp_img=img, roi=roi, threshold=0.54, use_grayscale=True, mode="all"
                )
            ).success:
                bottom_match = res_bottom.matches[0]
                roi_height = bottom_match.center[1] - off_bottom_of_descr - match.region[1]
            crop_roi = [
                match.region[0] + item_descr_pad,
                match.region[1] + item_descr_pad,
                item_descr_width - 2 * item_descr_pad,
                roi_height,
            ]
            cropped_descr = crop(img, crop_roi)
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
