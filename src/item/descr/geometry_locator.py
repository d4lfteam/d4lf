from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from src.item.data.item_type import ItemType

if TYPE_CHECKING:
    import numpy as np

    from src.item.data.affix import Affix
    from src.item.descr.texture import BulletSearchTrace
    from src.item.models import Item
    from src.template_finder import TemplateMatch

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
FailureReason = Literal[
    "missing_separator", "insufficient_affix_rows", "missing_aspect_marker", "marker_below_threshold"
]


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


@dataclass(frozen=True)
class TemplateMatchTrace:
    name: str
    center: tuple[int, int]
    region: list[int]
    confidence: float


@dataclass
class BulletMatchDiagnostics:
    raw: list[TemplateMatchTrace] = field(default_factory=list)
    rejected_outliers: list[TemplateMatchTrace] = field(default_factory=list)
    rejected_duplicates: list[TemplateMatchTrace] = field(default_factory=list)
    accepted: list[TemplateMatchTrace] = field(default_factory=list)
    suppressed_horadric_seal: list[TemplateMatchTrace] = field(default_factory=list)


@dataclass
class LocatorDiagnostics:
    separator: TemplateMatchTrace | None = None
    long_separator: TemplateMatchTrace | None = None
    affix_bullets: BulletMatchDiagnostics | None = None
    aspect_bullets: BulletMatchDiagnostics | None = None
    all_markers: list[LocatedMarker] | None = None
    selected_markers: list[LocatedMarker] = field(default_factory=list)
    failure_reason: FailureReason | None = None


@dataclass(frozen=True)
class DiagnosticLocatorResult:
    result: LocatorResult
    diagnostics: LocatorDiagnostics


def locate_affix_markers(
    *,
    tooltip_image: np.ndarray | None,
    item: Item,
    matched_affixes: list[Affix] | None = None,
    aspect_matched: bool = False,
    short_separator_match: TemplateMatch | None = None,
) -> LocatorResult:
    return _locate_affix_markers_core(
        tooltip_image, item, matched_affixes or [], aspect_matched, short_separator_match, None
    )


def locate_affix_markers_with_diagnostics(
    *,
    tooltip_image: np.ndarray | None,
    item: Item,
    matched_affixes: list[Affix] | None = None,
    aspect_matched: bool = False,
    short_separator_match: TemplateMatch | None = None,
) -> DiagnosticLocatorResult:
    diagnostics = LocatorDiagnostics()
    result = _locate_affix_markers_core(
        tooltip_image, item, matched_affixes or [], aspect_matched, short_separator_match, diagnostics
    )
    return DiagnosticLocatorResult(result, diagnostics)


def _locate_affix_markers_core(
    tooltip_image: np.ndarray | None,
    item: Item,
    matched_affixes: list[Affix],
    aspect_matched: bool,
    short_separator_match: TemplateMatch | None,
    diagnostics: LocatorDiagnostics | None,
) -> LocatorResult:
    if not matched_affixes and not aspect_matched:
        return LocatorResult(markers=[], reliable=True)

    all_markers = _locate_tts_guided_template(
        tooltip_image, item, matched_affixes, aspect_matched, short_separator_match, diagnostics
    )
    if all_markers is None:
        return LocatorResult(markers=[], reliable=False)

    if diagnostics is not None:
        diagnostics.all_markers = all_markers
    selected_markers = _select_requested_markers(item, matched_affixes, aspect_matched, all_markers)
    if diagnostics is not None:
        diagnostics.selected_markers = selected_markers
    has_requested_markers = _has_requested_markers(item, matched_affixes, aspect_matched, selected_markers)
    above_threshold = all(marker.confidence >= _BULLET_MATCH_THRESHOLD for marker in selected_markers)
    reliable = has_requested_markers and above_threshold

    if diagnostics is not None and not reliable:
        if aspect_matched and not any(marker.kind == "aspect" for marker in selected_markers):
            diagnostics.failure_reason = "missing_aspect_marker"
        elif not has_requested_markers:
            diagnostics.failure_reason = "insufficient_affix_rows"
        else:
            diagnostics.failure_reason = "marker_below_threshold"

    return LocatorResult(markers=selected_markers if reliable else [], reliable=reliable)


def _locate_tts_guided_template(
    tooltip_image: np.ndarray | None,
    item: Item,
    matched_affixes: list[Affix],
    aspect_matched: bool,
    short_separator_match: TemplateMatch | None,
    diagnostics: LocatorDiagnostics | None,
) -> list[LocatedMarker] | None:
    # Keep texture imports lazy so non-vision tests do not import Windows-only screenshot dependencies.
    from src.item.descr.texture import (  # noqa: PLC0415
        find_bullets_for_templates,
        find_bullets_for_templates_traced,
        find_seperator_long,
        find_seperator_short,
    )

    if tooltip_image is None:
        if diagnostics is not None:
            diagnostics.failure_reason = "missing_separator"
        return None

    separator_match = (
        short_separator_match
        if short_separator_match is not None
        else find_seperator_short(tooltip_image, threshold=_SEPARATOR_MATCH_THRESHOLD)
    )
    if separator_match is None:
        if diagnostics is not None:
            diagnostics.failure_reason = "missing_separator"
        return None

    if diagnostics is not None:
        diagnostics.separator = _to_template_match_trace(separator_match)
    markers: list[LocatedMarker] = []

    long_separator_match = find_seperator_long(tooltip_image, separator_match)
    if diagnostics is not None and long_separator_match is not None:
        diagnostics.long_separator = _to_template_match_trace(long_separator_match)

    if matched_affixes:
        bullet_search_kwargs = {
            "threshold": _BULLET_MATCH_THRESHOLD,
            "expected_count": len(item.inherent) + len(item.affixes),
            "max_y": long_separator_match.region[1] if long_separator_match is not None else None,
        }
        if diagnostics is None:
            affix_bullets = find_bullets_for_templates(
                tooltip_image, separator_match, _AFFIX_BULLET_TEMPLATE_REFS, **bullet_search_kwargs
            )
        else:
            affix_bullets, affix_trace = find_bullets_for_templates_traced(
                tooltip_image, separator_match, _AFFIX_BULLET_TEMPLATE_REFS, **bullet_search_kwargs
            )
            diagnostics.affix_bullets = _to_bullet_match_diagnostics(affix_trace)
        if item.item_type == ItemType.HoradricSeal and affix_bullets:
            if diagnostics is not None:
                diagnostics.affix_bullets.suppressed_horadric_seal = [_to_template_match_trace(affix_bullets[0])]
            affix_bullets = affix_bullets[1:]

        expected_affix_rows = len(item.inherent) + len(item.affixes)
        if len(affix_bullets) < expected_affix_rows:
            if diagnostics is not None:
                diagnostics.failure_reason = "insufficient_affix_rows"
            return None

        markers.extend(
            LocatedMarker(kind="affix", index=index, center=match.center, confidence=match.score)
            for index, match in enumerate(affix_bullets[:expected_affix_rows])
        )

    if aspect_matched and item.aspect is not None:
        if diagnostics is None:
            aspect_bullets = find_bullets_for_templates(
                tooltip_image,
                separator_match,
                _ASPECT_BULLET_TEMPLATE_REFS,
                threshold=_BULLET_MATCH_THRESHOLD,
                expected_count=1,
            )
        else:
            aspect_bullets, aspect_trace = find_bullets_for_templates_traced(
                tooltip_image,
                separator_match,
                _ASPECT_BULLET_TEMPLATE_REFS,
                threshold=_BULLET_MATCH_THRESHOLD,
                expected_count=1,
            )
            diagnostics.aspect_bullets = _to_bullet_match_diagnostics(aspect_trace)
        if aspect_bullets:
            best_match = max(aspect_bullets, key=lambda match: match.score)
            markers.append(LocatedMarker(kind="aspect", index=0, center=best_match.center, confidence=best_match.score))

    return markers


def _to_template_match_trace(match: TemplateMatch) -> TemplateMatchTrace:
    return TemplateMatchTrace(name=match.name, center=match.center, region=match.region, confidence=match.score)


def _to_bullet_match_diagnostics(trace: BulletSearchTrace) -> BulletMatchDiagnostics:
    return BulletMatchDiagnostics(
        raw=[_to_template_match_trace(match) for match in trace.raw],
        rejected_outliers=[_to_template_match_trace(match) for match in trace.rejected_outliers],
        rejected_duplicates=[_to_template_match_trace(match) for match in trace.rejected_duplicates],
        accepted=[_to_template_match_trace(match) for match in trace.accepted],
    )


def _select_requested_markers(
    item: Item, matched_affixes: list[Affix], aspect_matched: bool, markers: list[LocatedMarker]
) -> list[LocatedMarker]:
    requested_affix_rows = _requested_affix_rows(item, matched_affixes)
    selected = [marker for marker in markers if marker.kind == "affix" and marker.index in requested_affix_rows]
    if aspect_matched:
        selected.extend(marker for marker in markers if marker.kind == "aspect" and marker.index == 0)
    return selected


def _has_requested_markers(
    item: Item, matched_affixes: list[Affix], aspect_matched: bool, markers: list[LocatedMarker]
) -> bool:
    requested_affix_rows = _requested_affix_rows(item, matched_affixes)
    selected_affix_rows = {marker.index for marker in markers if marker.kind == "affix"}
    has_aspect_marker = any(marker.kind == "aspect" for marker in markers)
    return selected_affix_rows == requested_affix_rows and (not aspect_matched or has_aspect_marker)


def _requested_affix_rows(item: Item, matched_affixes: list[Affix]) -> set[int]:
    return {row_index for affix in matched_affixes if (row_index := _affix_row_index(item, affix)) is not None}


def _affix_row_index(item: Item, affix: Affix) -> int | None:
    for index, item_affix in enumerate(item.inherent + item.affixes):
        if item_affix is affix:
            return index
    for index, item_affix in enumerate(item.inherent + item.affixes):
        if item_affix == affix:
            return index
    return None
