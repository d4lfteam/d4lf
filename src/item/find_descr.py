from copy import copy
from typing import TYPE_CHECKING

from src.config.ui import ResManager
from src.item.data.rarity import ItemRarity
from src.template_finder import SearchResult, search
from src.utils.image_operations import crop
from src.utils.roi_operations import fit_roi_to_window_size

if TYPE_CHECKING:
    import numpy as np

    from src.template_finder import TemplateMatch

map_template_rarity = {
    "item_common_top_left": ItemRarity.Common,
    "item_leg_top_left": ItemRarity.Legendary,
    "item_magic_top_left": ItemRarity.Magic,
    "item_mythic_top_left": ItemRarity.Mythic,
    "item_rare_top_left": ItemRarity.Rare,
    "item_unique_top_left": ItemRarity.Unique,
}


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


def _template_search_in_roi(img: np.ndarray, roi: list[int] | tuple[int, int, int, int]) -> SearchResult:
    ok, fitted_roi = fit_roi_to_window_size(list(roi), ResManager().pos.window_dimensions)
    if ok:
        return search(ref=list(map_template_rarity.keys()), inp_img=img, roi=fitted_roi, threshold=0.8, mode="all")
    return SearchResult(success=False)


def _template_search_near_anchor(img: np.ndarray, anchor: tuple[int, int]) -> SearchResult:
    item_descr_width = ResManager().offsets.item_descr_width
    _, window_height = ResManager().pos.window_dimensions
    horizontal_padding = int(item_descr_width * 0.6)
    roi = [
        anchor[0] - item_descr_width - horizontal_padding,
        0,
        item_descr_width + (2 * horizontal_padding),
        window_height,
    ]
    return _template_search_in_roi(img, roi)


def _template_search_near_top_left(img: np.ndarray, top_left: tuple[int, int]) -> SearchResult:
    item_descr_width = ResManager().offsets.item_descr_width
    _, window_height = ResManager().pos.window_dimensions
    # Controller mode: selected item tooltips stay in a stable screen area, so start with a tighter ROI there.
    horizontal_padding = int(item_descr_width * 0.18)
    vertical_padding = int(window_height * 0.05)
    search_width = int(item_descr_width * 0.45) + (2 * horizontal_padding)
    search_height = int(window_height * 0.18) + (2 * vertical_padding)
    roi = [top_left[0] - horizontal_padding, top_left[1] - vertical_padding, search_width, search_height]
    return _template_search_in_roi(img, roi)


def _build_descr_result(
    img: np.ndarray, match: TemplateMatch
) -> tuple[bool, ItemRarity, np.ndarray, tuple[int, int, int, int]]:
    item_descr_width = ResManager().offsets.item_descr_width
    item_descr_pad = ResManager().offsets.item_descr_pad
    _, window_height = ResManager().pos.window_dimensions
    rarity = map_template_rarity[match.name.lower()]

    # find equipe template
    offset_top = int(window_height * 0.03)
    roi_y = match.region[1] + offset_top
    search_height = window_height - roi_y - offset_top
    delta_x = int(item_descr_width * 0.03)
    roi = [match.region[0] - delta_x, roi_y, item_descr_width + 2 * delta_x, search_height]

    refs = ["item_seperator_short_rare", "item_seperator_short_legendary", "item_seperator_short_mythic"]
    sep_short = search(refs, img, 0.8, roi, True, mode="first", do_multi_process=False)

    if not sep_short.success:
        return False, None, None, None

    off_bottom_of_descr = ResManager().offsets.item_descr_off_bottom_edge
    roi_height = ResManager().pos.window_dimensions[1] - (2 * off_bottom_of_descr) - match.region[1]
    if (
        res_bottom := search(
            ref=["item_bottom_edge"], inp_img=img, roi=roi, threshold=0.54, use_grayscale=True, mode="all"
        )
    ).success:
        roi_height = res_bottom.matches[0].center[1] - off_bottom_of_descr - match.region[1]
    crop_roi = [
        match.region[0] + item_descr_pad,
        match.region[1] + item_descr_pad,
        item_descr_width - 2 * item_descr_pad,
        roi_height,
    ]
    cropped_descr = crop(img, crop_roi)
    return True, rarity, cropped_descr, crop_roi


def find_descr(
    img: np.ndarray, anchor: tuple[int, int]
) -> tuple[bool, ItemRarity, np.ndarray, tuple[int, int, int, int]]:
    res_left = _template_search(img, anchor[0], ResManager().roi.rel_descr_search_left)
    res_right = _template_search(img, anchor[0], ResManager().roi.rel_descr_search_right)

    res = _choose_best_result(res_left, res_right)

    if res is not None and res.success:
        return _build_descr_result(img, res.matches[0])

    return False, None, None, None


def find_descr_anywhere(
    img: np.ndarray,
    anchor: tuple[int, int],
    expected_rarity: ItemRarity | None = None,
    preferred_top_left: tuple[int, int] | None = None,
) -> tuple[bool, ItemRarity, np.ndarray, tuple[int, int, int, int]]:
    search_results = []
    if preferred_top_left is not None:
        # Controller mode: try the learned tooltip region first, then fall back to the broader anchor-based scan.
        search_results.append(_template_search_near_top_left(img, preferred_top_left))
    search_results.append(_template_search_near_anchor(img, anchor))

    for res in search_results:
        if not res.success:
            continue
        if preferred_top_left is not None:
            matches = sorted(
                res.matches,
                key=lambda match: (
                    abs(match.region[0] - preferred_top_left[0]) + abs(match.region[1] - preferred_top_left[1])
                ),
            )
        else:
            matches = sorted(res.matches, key=lambda match: abs(match.region[0] - anchor[0]))
        candidate_groups = [matches]
        if expected_rarity is not None:
            preferred_matches = [
                match for match in matches if map_template_rarity.get(match.name.lower()) == expected_rarity
            ]
            if preferred_matches:
                candidate_groups = [preferred_matches, matches]

        for candidate_matches in candidate_groups:
            if not candidate_matches:
                continue
            for match in candidate_matches:
                found, rarity, cropped_descr, item_roi = _build_descr_result(img, match)
                if found:
                    return found, rarity, cropped_descr, item_roi

    return False, None, None, None
