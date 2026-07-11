from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.item.data.item_type import ItemType

if TYPE_CHECKING:
    import numpy as np

    from src.item.data.affix import Affix
    from src.item.models import Item

_AFFIX_BULLET_TEMPLATE_REFS = [
    "affix_bullet_point_1",
    "affix_bullet_point_1_medium",
    "affix_bullet_point_2",
    "affix_bullet_point_2_medium",
    "greater_affix_bullet_point_1",
    "greater_affix_bullet_point_1_medium",
    "greater_affix_bullet_point_1080p_special",
    "greater_affix_bullet_point_masterworked",
    "greater_affix_bullet_point_masterworked_medium",
    "greater_affix_bullet_point_masterworked_medium_1080p_special",
    "masterworking_affix_bullet",
    "masterworking_affix_bullet_2",
    "masterworking_affix_bullet_2_medium",
    "masterworking_affix_bullet_medium",
    "masterworking_affix_bullet_medium_1080p_special",
    "rerolled_bullet_point_1",
    "rerolled_bullet_point_1_medium",
    "rerolled_bullet_point_2",
    "rerolled_bullet_point_2_medium",
    "seal_set_bullet_point",
    "seal_set_bullet_point_1080p_special",
    "seal_set_bullet_point_medium",
    "tempered_affix_bullet_point_1",
    "tempered_affix_bullet_point_1_medium",
    "tempered_affix_bullet_point_2",
    "tempered_affix_bullet_point_2_medium",
    "tempered_affix_bullet_point_3",
    "tempered_affix_bullet_point_3_medium",
    "tempered_affix_bullet_point_4",
    "tempered_affix_bullet_point_4_medium",
    "tempered_affix_bullet_point_5",
    "tempered_affix_bullet_point_5_medium",
    "tempered_affix_bullet_point_6",
    "tempered_affix_bullet_point_6_medium",
]
_ASPECT_BULLET_TEMPLATE_REFS = [
    "legendary_bullet_point",
    "legendary_bullet_point_medium",
    "mythic_bullet_point",
    "mythic_bullet_point_1080p_special",
    "mythic_bullet_point_medium",
    "mythic_bullet_point_medium_1080p_special",
    "unique_bullet_point",
    "unique_bullet_point_medium",
]
_SEPARATOR_MATCH_THRESHOLD = 0.6
_BULLET_MATCH_THRESHOLD = 0.8


@dataclass(frozen=True)
class LocatedMarker:
    kind: str
    index: int
    center: tuple[int, int]
    confidence: float


@dataclass(frozen=True)
class LocatorResult:
    markers: list[LocatedMarker]
    reliable: bool


def locate_affix_markers(
    *,
    tooltip_image: np.ndarray | None,
    item: Item,
    matched_affixes: list[Affix] | None = None,
    aspect_matched: bool = False,
) -> LocatorResult:
    matched_affixes = matched_affixes or []
    if not matched_affixes and not aspect_matched:
        return LocatorResult(markers=[], reliable=True)

    all_markers = _locate_tts_guided_template(tooltip_image, item, matched_affixes, aspect_matched)
    if all_markers is None:
        return LocatorResult(markers=[], reliable=False)

    markers = _select_requested_markers(item, matched_affixes, aspect_matched, all_markers)
    reliable = _has_requested_markers(matched_affixes, aspect_matched, markers) and all(
        marker.confidence >= _BULLET_MATCH_THRESHOLD for marker in markers
    )
    return LocatorResult(markers=markers if reliable else [], reliable=reliable)


def _locate_tts_guided_template(
    tooltip_image: np.ndarray | None, item: Item, matched_affixes: list[Affix], aspect_matched: bool
) -> list[LocatedMarker] | None:
    # Keep texture imports lazy so non-vision tests do not import Windows-only screenshot dependencies.
    from src.item.descr.texture import find_bullets_for_templates, find_seperator_short  # noqa: PLC0415

    if tooltip_image is None:
        return None

    sep_short_match = find_seperator_short(tooltip_image, threshold=_SEPARATOR_MATCH_THRESHOLD)
    if sep_short_match is None:
        return None

    markers = []
    if matched_affixes:
        affix_bullets = find_bullets_for_templates(
            tooltip_image,
            sep_short_match,
            _AFFIX_BULLET_TEMPLATE_REFS,
            threshold=_BULLET_MATCH_THRESHOLD,
            expected_count=len(item.inherent) + len(item.affixes),
        )

        if item.item_type == ItemType.HoradricSeal and affix_bullets:
            affix_bullets = affix_bullets[1:]

        expected_affix_rows = len(item.inherent) + len(item.affixes)
        if len(affix_bullets) < expected_affix_rows:
            return None

        markers.extend(
            LocatedMarker(kind="affix", index=index, center=match.center, confidence=match.score)
            for index, match in enumerate(affix_bullets[:expected_affix_rows])
        )
    if aspect_matched and item.aspect is not None:
        aspect_bullets = find_bullets_for_templates(
            tooltip_image,
            sep_short_match,
            _ASPECT_BULLET_TEMPLATE_REFS,
            threshold=_BULLET_MATCH_THRESHOLD,
            expected_count=1,
        )
        if aspect_bullets:
            best = max(aspect_bullets, key=lambda m: m.score)
            markers.append(LocatedMarker(kind="aspect", index=0, center=best.center, confidence=best.score))

    return markers


def _select_requested_markers(
    item: Item, matched_affixes: list[Affix], aspect_matched: bool, markers: list[LocatedMarker]
) -> list[LocatedMarker]:
    requested_affix_rows = {
        row_index for affix in matched_affixes if (row_index := _affix_row_index(item, affix)) is not None
    }
    selected = [marker for marker in markers if marker.kind == "affix" and marker.index in requested_affix_rows]
    if aspect_matched:
        selected.extend(marker for marker in markers if marker.kind == "aspect" and marker.index == 0)
    return selected


def _has_requested_markers(matched_affixes: list[Affix], aspect_matched: bool, markers: list[LocatedMarker]) -> bool:
    affix_marker_count = sum(1 for marker in markers if marker.kind == "affix")
    has_aspect_marker = any(marker.kind == "aspect" for marker in markers)
    return affix_marker_count == len(matched_affixes) and (not aspect_matched or has_aspect_marker)


def _affix_row_index(item: Item, affix: Affix) -> int | None:
    for index, item_affix in enumerate(item.inherent + item.affixes):
        if item_affix is affix:
            return index
    for index, item_affix in enumerate(item.inherent + item.affixes):
        if item_affix == affix:
            return index
    return None
