"""Annotation rendering for cropped tooltip replay."""

from typing import TYPE_CHECKING

import cv2

if TYPE_CHECKING:
    import numpy as np

    from src.perception import BulletMatchDiagnostics, DiagnosticLocatorResult, TemplateMatchTrace

from src.tools.replay.common import font_scale as _font_scale
from src.tools.replay.diagnostics import _trace_label

RAW_MATCH_COLOR = (128, 128, 128)
REJECTED_MATCH_COLOR = (0, 165, 255)
ACCEPTED_MATCH_COLOR = (255, 255, 0)
FINAL_MARKER_COLOR = (93, 252, 35)
FAILURE_COLOR = (0, 0, 255)
TEXT_COLOR = (255, 255, 255)
BACKGROUND_COLOR = (30, 30, 30)


def _draw_trace(
    image: np.ndarray, trace: TemplateMatchTrace, color: tuple[int, int, int], stage: str, font_scale: float
) -> None:
    x, y, width, height = trace.region
    cv2.rectangle(image, (x, y), (x + width, y + height), color, 2)
    cv2.putText(
        image,
        f"{stage}: {_trace_label(trace)}",
        (max(0, x), max(15, y - 4)),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        color,
        1,
        cv2.LINE_AA,
    )


def _draw_bullet_diagnostics(image: np.ndarray, stage: str, diagnostics: BulletMatchDiagnostics | None) -> None:
    if diagnostics is None:
        return
    font_scale = _font_scale(image)
    for trace in diagnostics.raw:
        _draw_trace(image, trace, RAW_MATCH_COLOR, f"{stage} raw", font_scale)
    for trace in diagnostics.rejected_outliers + diagnostics.rejected_duplicates:
        _draw_trace(image, trace, REJECTED_MATCH_COLOR, f"{stage} rejected", font_scale)
    for trace in diagnostics.accepted:
        _draw_trace(image, trace, ACCEPTED_MATCH_COLOR, f"{stage} accepted", font_scale)


def _draw_legend(image: np.ndarray) -> None:
    entries = [
        (RAW_MATCH_COLOR, "Raw matches"),
        (REJECTED_MATCH_COLOR, "Rejected matches"),
        (ACCEPTED_MATCH_COLOR, "Accepted template regions"),
        (FINAL_MARKER_COLOR, "Final production markers"),
    ]
    font_scale = _font_scale(image)
    line_height = max(20, int(25 * font_scale))
    panel_height = line_height * (len(entries) + 1) + 10
    panel_width = min(image.shape[1], max(280, int(image.shape[1] * 0.7)))
    panel_top = max(0, image.shape[0] - panel_height)
    overlay = image.copy()
    cv2.rectangle(overlay, (0, panel_top), (panel_width, image.shape[0]), BACKGROUND_COLOR, -1)
    cv2.addWeighted(overlay, 0.78, image, 0.22, 0, image)
    cv2.putText(
        image,
        "Template matching replay",
        (8, panel_top + line_height),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        TEXT_COLOR,
        1,
    )
    for row, (color, label) in enumerate(entries, start=1):
        y = panel_top + line_height * (row + 1) - 5
        cv2.rectangle(image, (8, y - line_height + 5), (24, y + 2), color, -1)
        cv2.putText(image, label, (32, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, TEXT_COLOR, 1)


def _annotate(image: np.ndarray, diagnostic_result: DiagnosticLocatorResult, marker_size: int) -> np.ndarray:
    annotated = image.copy()
    diagnostics = diagnostic_result.diagnostics
    font_scale = _font_scale(annotated)
    if diagnostics.separator is not None:
        _draw_trace(annotated, diagnostics.separator, ACCEPTED_MATCH_COLOR, "separator", font_scale)
    if diagnostics.long_separator is not None:
        _draw_trace(annotated, diagnostics.long_separator, ACCEPTED_MATCH_COLOR, "long separator", font_scale)
    _draw_bullet_diagnostics(annotated, "affix", diagnostics.affix_bullets)
    _draw_bullet_diagnostics(annotated, "aspect", diagnostics.aspect_bullets)
    _draw_legend(annotated)

    half_size = max(1, marker_size // 2)
    for marker in diagnostic_result.result.markers:
        x, y = marker.center
        cv2.rectangle(annotated, (x - half_size, y - half_size), (x + half_size, y + half_size), FINAL_MARKER_COLOR, -1)
        cv2.putText(
            annotated,
            f"{marker.kind}[{marker.index}]",
            (max(0, x + half_size + 4), max(15, y)),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            FINAL_MARKER_COLOR,
            1,
            cv2.LINE_AA,
        )

    if not diagnostic_result.result.reliable:
        reason = diagnostics.failure_reason or "unknown failure"
        failure_text = f"FAILURE: {reason.replace('_', ' ')}"
        cv2.rectangle(annotated, (0, 0), (annotated.shape[1] - 1, 35), FAILURE_COLOR, -1)
        cv2.putText(annotated, failure_text, (8, 25), cv2.FONT_HERSHEY_SIMPLEX, font_scale, TEXT_COLOR, 2, cv2.LINE_AA)
    return annotated
