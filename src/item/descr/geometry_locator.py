from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.item.data.item_type import ItemType

if TYPE_CHECKING:
    import numpy as np

    from src.item.data.affix import Affix
    from src.item.data.rarity import ItemRarity
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
_SEPARATOR_MATCH_THRESHOLD = 0.55
_BULLET_MATCH_THRESHOLD = 0.72


@dataclass(frozen=True)
class AffixMarkerRequest:
    tooltip_image: np.ndarray | None
    item: Item
    matched_affixes: list[Affix] = field(default_factory=list)
    aspect_matched: bool = False
    minimum_confidence: float = _BULLET_MATCH_THRESHOLD


@dataclass(frozen=True)
class LocatedMarker:
    kind: str
    index: int
    center: tuple[int, int]
    confidence: float


@dataclass(frozen=True)
class LocatorResult:
    strategy: str
    tooltip_found: bool
    markers: list[LocatedMarker]
    confidence: float
    failure_reason: str | None
    reliable: bool


class AffixMarkerLocator:
    def locate(self, request: AffixMarkerRequest) -> LocatorResult:
        if not request.matched_affixes and not request.aspect_matched:
            return LocatorResult(
                strategy="none",
                tooltip_found=request.tooltip_image is not None,
                markers=[],
                confidence=1.0,
                failure_reason=None,
                reliable=True,
            )

        result = _locate_tts_guided_template(request)
        reliable = result.tooltip_found and result.confidence >= request.minimum_confidence
        markers = _select_requested_markers(request, result.markers) if reliable else []
        if reliable and _has_requested_markers(request, markers):
            return LocatorResult(
                strategy=result.strategy,
                tooltip_found=result.tooltip_found,
                markers=markers,
                confidence=result.confidence,
                failure_reason=None,
                reliable=True,
            )

        return LocatorResult(
            strategy=result.strategy,
            tooltip_found=result.tooltip_found,
            markers=[],
            confidence=result.confidence,
            failure_reason=result.failure_reason or "No reliable marker coordinates found",
            reliable=False,
        )


def _affix_bullet_templates_for_item(_item: Item) -> list[str]:
    return _AFFIX_BULLET_TEMPLATE_REFS.copy()


def _aspect_bullet_templates_for_rarity(_rarity: ItemRarity | None) -> list[str]:
    return _ASPECT_BULLET_TEMPLATE_REFS.copy()


def _locate_tts_guided_template(request: AffixMarkerRequest) -> LocatorResult:
    # Keep texture imports lazy so non-vision tests do not import Windows-only screenshot dependencies.
    from src.item.descr.texture import find_bullets_for_templates, find_seperator_short  # noqa: PLC0415

    strategy = "tts-guided-template"
    image = request.tooltip_image
    if image is None:
        return _strategy_failure(strategy, tooltip_found=False, reason="Tooltip image is unavailable")

    sep_short_match = find_seperator_short(image, threshold=_SEPARATOR_MATCH_THRESHOLD)
    if sep_short_match is None:
        return _strategy_failure(strategy, tooltip_found=False, reason="Short separator not found")

    markers = []
    if request.matched_affixes:
        affix_template_list = _affix_bullet_templates_for_item(request.item)
        affix_bullets = find_bullets_for_templates(
            image,
            sep_short_match,
            affix_template_list,
            threshold=_BULLET_MATCH_THRESHOLD,
            expected_count=len(request.item.inherent) + len(request.item.affixes),
        )

        if request.item.item_type == ItemType.HoradricSeal and affix_bullets:
            affix_bullets = affix_bullets[1:]

        expected_affix_rows = len(request.item.inherent) + len(request.item.affixes)
        if len(affix_bullets) < expected_affix_rows:
            return _strategy_failure(
                strategy,
                tooltip_found=True,
                reason=f"Found {len(affix_bullets)} affix bullets for {expected_affix_rows} TTS affix rows",
            )

        markers.extend(
            LocatedMarker(kind="affix", index=index, center=match.center, confidence=match.score)
            for index, match in enumerate(affix_bullets[:expected_affix_rows])
        )

    if request.aspect_matched and request.item.aspect is not None:
        aspect_template_list = _aspect_bullet_templates_for_rarity(request.item.rarity)
        aspect_bullets = find_bullets_for_templates(
            image, sep_short_match, aspect_template_list, threshold=_BULLET_MATCH_THRESHOLD, expected_count=1
        )
        if aspect_bullets:
            best = max(aspect_bullets, key=lambda m: m.score)
            markers.append(LocatedMarker(kind="aspect", index=0, center=best.center, confidence=best.score))

    confidence = min((m.confidence for m in markers), default=0.0)
    return LocatorResult(
        strategy=strategy,
        tooltip_found=True,
        markers=markers,
        confidence=confidence,
        failure_reason=None,
        reliable=True,
    )


def _select_requested_markers(request: AffixMarkerRequest, markers: list[LocatedMarker]) -> list[LocatedMarker]:
    requested_affix_rows = {
        row_index
        for affix in request.matched_affixes
        if (row_index := _affix_row_index(request.item, affix)) is not None
    }
    selected = [marker for marker in markers if marker.kind == "affix" and marker.index in requested_affix_rows]
    if request.aspect_matched:
        selected.extend(marker for marker in markers if marker.kind == "aspect" and marker.index == 0)
    return selected


def _has_requested_markers(request: AffixMarkerRequest, markers: list[LocatedMarker]) -> bool:
    affix_marker_count = sum(1 for marker in markers if marker.kind == "affix")
    has_aspect_marker = any(marker.kind == "aspect" for marker in markers)
    return affix_marker_count == len(request.matched_affixes) and (not request.aspect_matched or has_aspect_marker)


def _affix_row_index(item: Item, affix: Affix) -> int | None:
    for index, item_affix in enumerate(item.inherent + item.affixes):
        if item_affix is affix:
            return index
    for index, item_affix in enumerate(item.inherent + item.affixes):
        if item_affix == affix:
            return index
    return None


def _strategy_failure(strategy: str, tooltip_found: bool, reason: str) -> LocatorResult:
    return LocatorResult(
        strategy=strategy,
        tooltip_found=tooltip_found,
        markers=[],
        confidence=0.0,
        failure_reason=reason,
        reliable=False,
    )
