import math

import numpy as np

from src.config.ui import ResManager
from src.template_finder import TemplateMatch, search


def find_seperator_short(img_item_descr: np.ndarray, threshold: float = 0.62) -> TemplateMatch:
    refs = ["item_seperator_short_rare", "item_seperator_short_legendary", "item_seperator_short_mythic"]
    roi = [
        0,
        int(ResManager().offsets.find_seperator_short_offset_top / 5),
        img_item_descr.shape[1],
        ResManager().offsets.find_seperator_short_offset_top,
    ]
    if not (
        sep_short := search(
            refs, img_item_descr, threshold, roi, use_grayscale=True, mode="all", do_multi_process=False
        )
    ).success:
        return None
    sorted_matches = sorted(sep_short.matches, key=lambda match: match.center[1])
    return sorted_matches[0]


def find_bullets_for_templates(
    img_item_descr: np.ndarray, sep_short_match: TemplateMatch, template_list: list[str], threshold: float = 0.80
) -> list[TemplateMatch]:
    """Search for bullet icons using an explicit template list instead of all possible bullet types."""
    return _find_bullets(img_item_descr, sep_short_match, template_list, threshold, "all")


def _filter_outliers(template_matches: list[TemplateMatch]) -> list[TemplateMatch]:
    # Extract center[0] values
    centers_x = [tm.center[0] for tm in template_matches]
    # Calculate the median
    if not centers_x:
        return []
    target_center_x = np.min(centers_x)
    # Filter out the outliers
    return [tm for tm in template_matches if abs(tm.center[0] - target_center_x) < 1.2 * tm.region[2]]


def _find_bullets(
    img_item_descr: np.ndarray, sep_short_match: TemplateMatch, template_list: list[str], threshold: float, mode: str
) -> list[TemplateMatch]:
    img_height = img_item_descr.shape[0]
    roi_bullets = [0, sep_short_match.center[1], ResManager().offsets.find_bullet_points_width, img_height]
    all_bullets = search(
        ref=template_list, inp_img=img_item_descr, threshold=threshold, roi=roi_bullets, use_grayscale=True, mode=mode
    )
    if not all_bullets.success:
        return []
    all_bullets.matches = _filter_outliers(all_bullets.matches)
    # go through the matches and filter out the ones that are too close to each other. only keep the one with higher probability
    matches_dict = {}
    for match in all_bullets.matches:
        match_exists = False
        for center in matches_dict:
            if math.sqrt((center[0] - match.center[0]) ** 2 + (center[1] - match.center[1]) ** 2) <= 10:
                if match.score > matches_dict[center].score:
                    matches_dict[center] = match
                match_exists = True
                break
        if not match_exists:
            matches_dict[match.center] = match
    filtered_matches = list(matches_dict.values())
    return sorted(filtered_matches, key=lambda match: match.center[1])
