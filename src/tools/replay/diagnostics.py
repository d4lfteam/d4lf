"""Logging helpers for cropped tooltip replay diagnostics."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.perception import BulletMatchDiagnostics, DiagnosticLocatorResult, TemplateMatchTrace

LOGGER = logging.getLogger("d4lf")


def _trace_label(trace: TemplateMatchTrace) -> str:
    return f"{trace.name} ({trace.confidence:.2f})"


def _log_trace_group(stage: str, traces: list[TemplateMatchTrace]) -> None:
    LOGGER.info("%s: count=%d", stage, len(traces))
    for trace in traces:
        LOGGER.info(
            "%s: template=%s center=%s region=%s confidence=%.4f",
            stage,
            trace.name,
            trace.center,
            trace.region,
            trace.confidence,
        )


def _log_bullet_diagnostics(stage: str, diagnostics: BulletMatchDiagnostics | None) -> None:
    if diagnostics is None:
        LOGGER.info("%s: unavailable", stage)
        return
    _log_trace_group(f"{stage}.raw", diagnostics.raw)
    _log_trace_group(f"{stage}.rejected_outliers", diagnostics.rejected_outliers)
    _log_trace_group(f"{stage}.rejected_duplicates", diagnostics.rejected_duplicates)
    _log_trace_group(f"{stage}.accepted", diagnostics.accepted)


def _log_diagnostics(diagnostic_result: DiagnosticLocatorResult) -> None:
    diagnostics = diagnostic_result.diagnostics
    if diagnostics.separator is None:
        LOGGER.info("separator: unavailable")
    else:
        _log_trace_group("separator", [diagnostics.separator])
    if diagnostics.long_separator is None:
        LOGGER.info("long_separator: unavailable")
    else:
        _log_trace_group("long_separator", [diagnostics.long_separator])
    _log_bullet_diagnostics("affix_bullets", diagnostics.affix_bullets)
    _log_bullet_diagnostics("aspect_bullets", diagnostics.aspect_bullets)
    if diagnostics.all_markers is None:
        LOGGER.info("all_markers: unavailable")
    else:
        for marker in diagnostics.all_markers:
            LOGGER.info(
                "all_markers: kind=%s index=%d center=%s confidence=%.4f",
                marker.kind,
                marker.index,
                marker.center,
                marker.confidence,
            )
    for marker in diagnostics.selected_markers:
        LOGGER.info(
            "Selected marker: kind=%s index=%d center=%s confidence=%.4f",
            marker.kind,
            marker.index,
            marker.center,
            marker.confidence,
        )
    for marker in diagnostic_result.result.markers:
        LOGGER.info(
            "Final marker: kind=%s index=%d center=%s confidence=%.4f",
            marker.kind,
            marker.index,
            marker.center,
            marker.confidence,
        )
