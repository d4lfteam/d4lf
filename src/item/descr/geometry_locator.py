from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.config.ui import ResManager
from src.item.data.affix import AffixType
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.texture import find_bullets_for_templates, find_seperator_short

if TYPE_CHECKING:
    import numpy as np

    from src.item.data.affix import Affix
    from src.item.filter import FilterResult
    from src.item.models import Item

LOGGER = logging.getLogger(__name__)

_ASPECT_BULLET_REFS_BY_RARITY: dict[ItemRarity, list[str]] = {
    ItemRarity.Legendary: ["legendary_bullet_point"],
    ItemRarity.Set: ["legendary_bullet_point"],
    ItemRarity.Unique: ["unique_bullet_point"],
    ItemRarity.Mythic: ["mythic_bullet_point"],
}
_ALL_ASPECT_BULLET_REFS = ["legendary_bullet_point", "unique_bullet_point", "mythic_bullet_point"]
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


def _affix_bullet_templates_for_item(item: Item) -> list[str]:
    """Build the minimal affix bullet template list based on TTS-known affix types and item kind."""
    all_affixes = item.inherent + item.affixes
    affix_types = {affix.type for affix in all_affixes}

    base: list[str] = []

    # Greater affix and masterworking bullets: only when TTS confirms greater affixes are present.
    if AffixType.greater in affix_types:
        base += [
            "greater_affix_bullet_point_1",
            "greater_affix_bullet_point_masterworked",
            "masterworking_affix_bullet",
            "masterworking_affix_bullet_2",
        ]

    # Seal bullets: only for HoradricSeal items or Set-rarity items.
    if item.item_type == ItemType.HoradricSeal or item.rarity == ItemRarity.Set:
        base.append("seal_set_bullet_point")

    # Normal affix bullets are always needed.
    base += [f"affix_bullet_point_{x}" for x in range(1, 3)]

    # Rerolled bullets: only when TTS reports at least one rerolled affix.
    if AffixType.rerolled in affix_types:
        base += [f"rerolled_bullet_point_{x}" for x in range(1, 3)]

    # Tempered bullets: only when TTS reports at least one tempered affix.
    if AffixType.tempered in affix_types:
        base += [f"tempered_affix_bullet_point_{x}" for x in range(1, 7)]

    templates = [f"{t}_medium" for t in base] + base

    # Resolution-specific extras (1080p and lower).
    if ResManager().resolution[1] <= 1200:
        if AffixType.greater in affix_types:
            templates += [
                "greater_affix_bullet_point_1080p_special",
                "greater_affix_bullet_point_masterworked_medium_1080p_special",
                "masterworking_affix_bullet_medium_1080p_special",
            ]
        if item.item_type == ItemType.HoradricSeal or item.rarity == ItemRarity.Set:
            templates.append("seal_set_bullet_point_1080p_special")

    return templates


def _aspect_bullet_templates_for_rarity(rarity: ItemRarity | None) -> list[str]:
    """Build the minimal aspect bullet template list based on TTS-known item rarity."""
    base = _ASPECT_BULLET_REFS_BY_RARITY.get(rarity, _ALL_ASPECT_BULLET_REFS) if rarity else _ALL_ASPECT_BULLET_REFS
    templates = [f"{t}_medium" for t in base] + list(base)
    # The 1080p special mythic templates are only added when mythic is a candidate.
    if ResManager().resolution[1] <= 1200 and rarity in (ItemRarity.Mythic, None):
        templates += ["mythic_bullet_point_1080p_special", "mythic_bullet_point_medium_1080p_special"]
    return templates


def _locate_tts_guided_template(request: AffixMarkerRequest) -> LocatorResult:
    strategy = "tts-guided-template"
    image = request.tooltip_image
    if image is None:
        return _strategy_failure(strategy, tooltip_found=False, reason="Tooltip image is unavailable")

    sep_short_match = find_seperator_short(image, threshold=_SEPARATOR_MATCH_THRESHOLD)
    if sep_short_match is None:
        return _strategy_failure(strategy, tooltip_found=False, reason="Short separator not found")

    affix_template_list = _affix_bullet_templates_for_item(request.item)
    affix_bullets = find_bullets_for_templates(
        image, sep_short_match, affix_template_list, threshold=_BULLET_MATCH_THRESHOLD
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

    markers = [
        LocatedMarker(kind="affix", index=index, center=match.center, confidence=match.score)
        for index, match in enumerate(affix_bullets[:expected_affix_rows])
    ]

    if request.item.aspect is not None:
        aspect_template_list = _aspect_bullet_templates_for_rarity(request.item.rarity)
        aspect_bullets = find_bullets_for_templates(
            image, sep_short_match, aspect_template_list, threshold=_BULLET_MATCH_THRESHOLD
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


def apply_marker_locations(item: Item, filter_result: FilterResult, locator_result: LocatorResult) -> None:
    if not locator_result.reliable:
        LOGGER.debug(
            "Skipping affix marker locations from %s: %s", locator_result.strategy, locator_result.failure_reason
        )
        return

    affix_rows = item.inherent + item.affixes
    marker_by_row = {(marker.kind, marker.index): marker for marker in locator_result.markers}
    for matched in filter_result.matched:
        for affix in matched.matched_affixes:
            row_index = _affix_row_index(item, affix)
            if row_index is None:
                continue
            marker = marker_by_row.get(("affix", row_index))
            if marker is not None and row_index < len(affix_rows):
                affix.loc = marker.center

    if item.aspect is not None and any(matched.aspect_match for matched in filter_result.matched):
        marker = marker_by_row.get(("aspect", 0))
        if marker is not None:
            item.aspect.loc = marker.center


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
