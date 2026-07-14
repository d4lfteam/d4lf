import math
from dataclasses import dataclass, field

import numpy as np

from src.config.ui import ResManager
from src.template_finder import TemplateMatch, search

_LONG_SEPARATOR_TEMPLATE_REFS = [
    "item_seperator_long_magic",
    "item_seperator_long_legendary",
    "item_seperator_long_mythic",
]
_SHORT_SEPARATOR_TEMPLATE_REFS = [
    "item_seperator_short_magic",
    "item_seperator_short_rare",
    "item_seperator_short_legendary",
    "item_seperator_short_mythic",
]


@dataclass
class BulletSearchTrace:
    raw: list[TemplateMatch] = field(default_factory=list)
    rejected_outliers: list[TemplateMatch] = field(default_factory=list)
    rejected_duplicates: list[TemplateMatch] = field(default_factory=list)
    accepted: list[TemplateMatch] = field(default_factory=list)


def find_seperator_short(
    img_item_descr: np.ndarray, threshold: float = 0.62, *, roi: list[int] | None = None, mode: str = "all"
) -> TemplateMatch | None:
    if roi is None:
        roi = [
            0,
            int(ResManager().offsets.find_seperator_short_offset_top / 5),
            img_item_descr.shape[1],
            ResManager().offsets.find_seperator_short_offset_top,
        ]
    if not (
        sep_short := search(
            _SHORT_SEPARATOR_TEMPLATE_REFS,
            inp_img=img_item_descr,
            threshold=threshold,
            roi=roi,
            use_grayscale=True,
            mode=mode,
            do_multi_process=False,
        )
    ).success:
        return None
    if mode == "first":
        return sep_short.matches[0]
    return min(sep_short.matches, key=lambda match: match.center[1])


def find_seperator_long(
    img_item_descr: np.ndarray, short_separator_match: TemplateMatch, threshold: float = 0.62
) -> TemplateMatch | None:
    roi = [
        0,
        short_separator_match.center[1],
        img_item_descr.shape[1],
        img_item_descr.shape[0] - short_separator_match.center[1],
    ]
    if not (
        long_separator := search(
            _LONG_SEPARATOR_TEMPLATE_REFS,
            img_item_descr,
            threshold,
            roi,
            use_grayscale=True,
            mode="all",
            do_multi_process=False,
        )
    ).success:
        return None
    return min(long_separator.matches, key=lambda match: match.region[1])


def find_bullets_for_templates(
    img_item_descr: np.ndarray,
    sep_short_match: TemplateMatch,
    template_list: list[str],
    threshold: float = 0.80,
    expected_count: int | None = None,
    max_y: int | None = None,
) -> list[TemplateMatch]:
    matches, _ = _find_bullets_for_templates(
        img_item_descr,
        sep_short_match,
        template_list,
        threshold=threshold,
        expected_count=expected_count,
        max_y=max_y,
        collect_trace=False,
    )
    return matches


def _filter_outliers(template_matches: list[TemplateMatch]) -> list[TemplateMatch]:
    # Extract center[0] values
    centers_x = [tm.center[0] for tm in template_matches]
    if not centers_x:
        return []
    # Select the leftmost center
    target_center_x = np.min(centers_x)
    # Filter out the outliers
    return [tm for tm in template_matches if abs(tm.center[0] - target_center_x) < 1.2 * tm.region[2]]


def _dedupe_matches(template_matches: list[TemplateMatch]) -> list[TemplateMatch]:
    matches_dict = {}
    for match in template_matches:
        match_exists = False
        for center in matches_dict:
            if math.sqrt((center[0] - match.center[0]) ** 2 + (center[1] - match.center[1]) ** 2) <= 10:
                if match.score > matches_dict[center].score:
                    matches_dict[center] = match
                match_exists = True
                break
        if not match_exists:
            matches_dict[match.center] = match
    return list(matches_dict.values())


def _filter_and_dedupe_matches(
    template_matches: list[TemplateMatch],
) -> tuple[list[TemplateMatch], list[TemplateMatch]]:
    filtered_matches = _filter_outliers(template_matches)
    return filtered_matches, _dedupe_matches(filtered_matches)


def find_bullets_for_templates_traced(
    img_item_descr: np.ndarray,
    sep_short_match: TemplateMatch,
    template_list: list[str],
    threshold: float = 0.80,
    expected_count: int | None = None,
    max_y: int | None = None,
) -> tuple[list[TemplateMatch], BulletSearchTrace]:
    matches, trace = _find_bullets_for_templates(
        img_item_descr,
        sep_short_match,
        template_list,
        threshold=threshold,
        expected_count=expected_count,
        max_y=max_y,
        collect_trace=True,
    )
    assert trace is not None
    return matches, trace


def _find_bullets_for_templates(
    img_item_descr: np.ndarray,
    sep_short_match: TemplateMatch,
    template_list: list[str],
    threshold: float,
    expected_count: int | None,
    max_y: int | None,
    collect_trace: bool,
) -> tuple[list[TemplateMatch], BulletSearchTrace | None]:
    img_height = img_item_descr.shape[0]
    bottom_y = min(max_y, img_height) if max_y is not None else img_height
    roi_bullets = [
        0,
        sep_short_match.center[1],
        ResManager().offsets.find_bullet_points_width,
        bottom_y - sep_short_match.center[1],
    ]

    def has_expected_bullet_rows(matches: list[TemplateMatch]) -> bool:
        if expected_count is None:
            return False
        _, accepted_matches = _filter_and_dedupe_matches(matches)
        return len(accepted_matches) >= expected_count

    all_bullets = search(
        ref=template_list,
        inp_img=img_item_descr,
        threshold=threshold,
        roi=roi_bullets,
        use_grayscale=True,
        mode="all",
        stop_condition=has_expected_bullet_rows if expected_count is not None else None,
    )
    if not all_bullets.success:
        return [], BulletSearchTrace() if collect_trace else None

    raw: list[TemplateMatch] = list(all_bullets.matches)
    after_outlier_filter, after_dedupe = _filter_and_dedupe_matches(raw)
    accepted = sorted(after_dedupe, key=lambda m: m.center[1])

    if not collect_trace:
        return accepted, None

    accepted_ids = {id(match) for match in after_outlier_filter}
    rejected_outliers = [match for match in raw if id(match) not in accepted_ids]

    deduped_ids = {id(match) for match in after_dedupe}
    rejected_duplicates = [match for match in after_outlier_filter if id(match) not in deduped_ids]

    trace = BulletSearchTrace(
        raw=raw, rejected_outliers=rejected_outliers, rejected_duplicates=rejected_duplicates, accepted=accepted
    )
    return accepted, trace
