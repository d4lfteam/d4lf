import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import cv2

from src.item import Affix, Aspect, Item, ItemType
from src.item.descr.geometry_locator import (
    BulletMatchDiagnostics,
    DiagnosticLocatorResult,
    TemplateMatchTrace,
    locate_affix_markers_with_diagnostics,
)
from src.logger import setup
from src.settings import get_ui_coordinates
from src.tools.replay_common import ReplayConfigurationError, load_replay_image, show_replay_result
from src.tools.replay_common import font_scale as _font_scale
from src.tools.replay_common import parse_resolution as _parse_resolution
from src.tools.replay_common import raise_configuration_error as _raise_configuration_error
from src.tools.replay_common import write_image as _write_image

if TYPE_CHECKING:
    import numpy as np

LOGGER = logging.getLogger("d4lf")

RAW_MATCH_COLOR = (128, 128, 128)
REJECTED_MATCH_COLOR = (0, 165, 255)
ACCEPTED_MATCH_COLOR = (255, 255, 0)
FINAL_MARKER_COLOR = (93, 252, 35)
FAILURE_COLOR = (0, 0, 255)
TEXT_COLOR = (255, 255, 255)
BACKGROUND_COLOR = (30, 30, 30)
_MARKER_THICKNESS_RATIO = 0.0047


@dataclass
class ReplayConfig:
    aspect_matched: bool
    game_resolution: str
    image_path: Path | str
    item: Item
    matched_row_indices: list[int]


@dataclass(frozen=True)
class ReplayResult:
    failure_reason: str | None
    output_path: Path
    reliable: bool


# BEGIN EDITABLE REPLAY CONFIGURATION
# Replace these values with the cropped tooltip and the Item captured from production.
REPLAY_CONFIG = ReplayConfig(
    image_path=Path(r"E:\Downloads\test5.png"),
    game_resolution="3840x2160",
    item=Item(
        inherent=[Affix(name="charm_slot")],
        affixes=[
            Affix(name="barrier_generation"),
            Affix(name="sescherons_fury_fury_generation"),
            Affix(name="berserkers_crucible_lucky_hit_up_to_a_chance_to_become_berserking"),
        ],
        item_type=ItemType.HoradricSeal,
    ),
    matched_row_indices=[2],
    aspect_matched=False,
)
# END EDITABLE REPLAY CONFIGURATION


def validate_replay_config(config: ReplayConfig) -> tuple[Path, np.ndarray]:
    """Validate replay inputs and return the normalized image path and decoded image."""
    image_path, image = load_replay_image(config.image_path, label="Tooltip image")

    _parse_resolution(config.game_resolution)
    if not isinstance(config.item, Item):
        _raise_configuration_error("Replay item must be an Item.")
    if not isinstance(config.aspect_matched, bool):
        _raise_configuration_error("Aspect-matched flag must be true or false.")
    if config.aspect_matched and config.item.aspect is None:
        _raise_configuration_error("Aspect-matched was requested, but the item has no aspect.")

    row_count = len(config.item.inherent) + len(config.item.affixes)
    indices = config.matched_row_indices
    if not isinstance(indices, list):
        _raise_configuration_error("Matched row indices must be provided as a list.")
    if any(not isinstance(index, int) or isinstance(index, bool) for index in indices):
        _raise_configuration_error("Matched row indices must be integers.")
    if len(indices) != len(set(indices)):
        _raise_configuration_error("Matched row indices contain a duplicate.")
    if any(index < 0 or index >= row_count for index in indices):
        _raise_configuration_error(f"Matched row index is out of range; item has {row_count} inherent and affix rows.")
    return image_path, image


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


def show_result(image: np.ndarray) -> None:
    """Display the replay result until the user closes the blocking window."""
    show_replay_result(image, "D4LF cropped tooltip replay")


def run_replay(config: ReplayConfig, *, display: bool = True) -> ReplayResult:
    """Run production matching against a cropped tooltip and save its explanation."""
    image_path, image = validate_replay_config(config)
    output_path = image_path.with_name(f"{image_path.stem}_template_matches.png")
    rows = config.item.inherent + config.item.affixes
    matched_affixes = [rows[index] for index in config.matched_row_indices]
    width, height = _parse_resolution(config.game_resolution)
    LOGGER.info(
        "Replay inputs: image=%s resolution=%sx%s matched_row_indices=%s aspect_matched=%s item=%s",
        image_path,
        width,
        height,
        config.matched_row_indices,
        config.aspect_matched,
        config.item,
    )

    resolution_manager = get_ui_coordinates()
    previous_resolution = "x".join(str(value) for value in resolution_manager.resolution)
    try:
        resolution_manager.set_resolution(config.game_resolution)
        diagnostic_result = locate_affix_markers_with_diagnostics(
            tooltip_image=image, item=config.item, matched_affixes=matched_affixes, aspect_matched=config.aspect_matched
        )
    finally:
        resolution_manager.set_resolution(previous_resolution)

    _log_diagnostics(diagnostic_result)
    LOGGER.info(
        "Replay reliability: reliable=%s failure_reason=%s",
        diagnostic_result.result.reliable,
        diagnostic_result.diagnostics.failure_reason,
    )
    marker_size = int(int(height * _MARKER_THICKNESS_RATIO) * 3)
    annotated = _annotate(image, diagnostic_result, marker_size)
    _write_image(output_path, annotated)
    LOGGER.info("Replay output: %s", output_path)
    if display:
        show_result(annotated)
    return ReplayResult(
        output_path=output_path,
        reliable=diagnostic_result.result.reliable,
        failure_reason=diagnostic_result.diagnostics.failure_reason,
    )


def main() -> int:
    setup(enable_stdout=True)
    try:
        result = run_replay(REPLAY_CONFIG)
    except ReplayConfigurationError as error:
        LOGGER.error("Replay configuration error: %s", error)
        return 2
    return 0 if result.reliable else 1


if __name__ == "__main__":
    raise SystemExit(main())
