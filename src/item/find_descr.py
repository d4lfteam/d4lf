from copy import copy
from typing import TYPE_CHECKING

from src.config.ui import ResManager
from src.item.data.rarity import ItemRarity
from src.template_finder import SearchResult, search
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


def _choose_best_result(res_left: SearchResult, res_right: SearchResult) -> SearchResult:
    if res_left.success and not res_right.success:
        return res_left
    if res_right.success and not res_left.success:
        return res_right
    if res_left.success and res_right.success:
        return res_left if res_left.matches[0].score > res_right.matches[0].score else res_right
    return SearchResult(success=False)


def _template_search(img: np.ndarray, anchor: int, roi: np.ndarray):
    roi_copy = copy(roi)
    roi_copy[0] += anchor
    ok, roi_left = fit_roi_to_window_size(roi_copy, ResManager().pos.window_dimensions)
    if ok:
        return search(ref=list(map_template_rarity.keys()), inp_img=img, roi=roi_left, threshold=0.8, mode="all")
    return SearchResult(success=False)


def find_descr(img: np.ndarray, anchor: tuple[int, int]) -> tuple[bool, ItemRarity, np.ndarray, tuple[int, int, int, int]]:
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

        refs = ["item_seperator_short_rare", "item_seperator_short_legendary", "item_seperator_short_mythic"]
        sep_short = search(refs, img, 0.8, roi, True, mode="first", do_multi_process=False)

        if sep_short.success:
            off_bottom_of_descr = ResManager().offsets.item_descr_off_bottom_edge
            roi_height = ResManager().pos.window_dimensions[1] - (2 * off_bottom_of_descr) - match.region[1]
            if (
                res_bottom := search(ref=["item_bottom_edge"], inp_img=img, roi=roi, threshold=0.54, use_grayscale=True, mode="all")
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

    return False, None, None, None
