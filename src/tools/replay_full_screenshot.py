import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import cv2

from src.config.ui import ResManager
from src.item.find_descr import DescrDetection, find_descr_with_diagnostics
from src.logger import setup

if TYPE_CHECKING:
    import numpy as np

    from src.template_finder import TemplateMatch


LOGGER = logging.getLogger("d4lf")

RAW_MATCH_COLOR = (128, 128, 128)
SEPARATOR_MATCH_COLOR = (255, 255, 0)
BOTTOM_MATCH_COLOR = (255, 0, 255)
CROP_COLOR = (0, 255, 0)
ANCHOR_COLOR = (0, 255, 255)
TEXT_COLOR = (255, 255, 255)
BACKGROUND_COLOR = (30, 30, 30)
FAILURE_COLOR = (0, 0, 255)


@dataclass
class ReplayConfig:
    image_path: Path | str
    game_resolution: str
    item_anchor: tuple[int, int]


class ReplayConfigurationError(ValueError):
    """Raised when the editable full-screenshot replay configuration cannot be used."""


@dataclass(frozen=True)
class ReplayResult:
    output_path: Path
    crop_path: Path | None
    found: bool
    failure_reason: str | None


# BEGIN EDITABLE REPLAY CONFIGURATION
# Replace these values with a full game screenshot and the hovered item's center.
# Configure the generated *_cropped.png in replay_cropped_tooltip.py for marker matching.
REPLAY_CONFIG = ReplayConfig(image_path=Path("path/to/image.png"), game_resolution="3840x2160", item_anchor=(261, 427))
# END EDITABLE REPLAY CONFIGURATION


def _raise_configuration_error(message: str) -> NoReturn:
    raise ReplayConfigurationError(message)


def _parse_resolution(resolution: str) -> tuple[int, int]:
    if not isinstance(resolution, str) or re.fullmatch(r"[1-9]\d*x[1-9]\d*", resolution) is None:
        _raise_configuration_error(f"Game resolution must use WIDTHxHEIGHT form, got {resolution!r}.")
    width, height = (int(value) for value in resolution.split("x"))
    return width, height


def validate_replay_config(config: ReplayConfig) -> tuple[Path, np.ndarray]:
    """Validate replay inputs and return the normalized full-screenshot path and decoded image."""
    try:
        image_path = Path(config.image_path)
    except TypeError:
        _raise_configuration_error(f"Full screenshot image path is invalid: {config.image_path!r}")
    if not image_path.exists():
        _raise_configuration_error(f"Full screenshot image path does not exist: {image_path}")
    if not image_path.is_file():
        _raise_configuration_error(f"Full screenshot image path is not a file: {image_path}")
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        _raise_configuration_error(f"Full screenshot image cannot be read: {image_path}")

    _parse_resolution(config.game_resolution)
    anchor = config.item_anchor
    if (
        not isinstance(anchor, (tuple, list))
        or len(anchor) != 2
        or any(not isinstance(value, int) or isinstance(value, bool) for value in anchor)
        or any(value < 0 for value in anchor)
    ):
        _raise_configuration_error("Item anchor must be a pair of non-negative integers.")
    return image_path, image


def _log_match(stage: str, match: TemplateMatch | None) -> None:
    if match is None:
        LOGGER.info("%s: unavailable", stage)
        return
    LOGGER.info(
        "%s: template=%s center=%s region=%s score=%.4f", stage, match.name, match.center, match.region, match.score
    )


def _log_detection(detection: DescrDetection) -> None:
    _log_match("rarity", detection.rarity_match)
    _log_match("separator", detection.separator_match)
    _log_match("bottom", detection.bottom_match)
    LOGGER.info(
        "crop: roi=%s shape=%s",
        detection.crop_roi,
        None if detection.cropped_descr is None else detection.cropped_descr.shape,
    )
    LOGGER.info(
        "Full replay detection: found=%s rarity=%s failure_reason=%s",
        detection.found,
        detection.rarity,
        detection.failure_reason,
    )


def _font_scale(image: np.ndarray) -> float:
    return max(0.45, min(1.0, image.shape[0] / 800))


def _draw_match(image: np.ndarray, label: str, match, color: tuple[int, int, int]) -> None:
    x, y, width, height = match.region
    font_scale = _font_scale(image)
    cv2.rectangle(image, (x, y), (x + width, y + height), color, 3)
    cv2.putText(
        image,
        f"{label}: {match.name} ({match.score:.2f})",
        (max(0, x), max(18, y - 6)),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        color,
        2,
        cv2.LINE_AA,
    )


def _draw_legend(image: np.ndarray) -> None:
    entries = [
        (RAW_MATCH_COLOR, "Detected rarity border"),
        (SEPARATOR_MATCH_COLOR, "Detected short separator"),
        (BOTTOM_MATCH_COLOR, "Detected bottom edge"),
        (CROP_COLOR, "Cropped tooltip saved"),
        (ANCHOR_COLOR, "Configured item anchor"),
    ]
    font_scale = _font_scale(image)
    line_height = max(20, int(25 * font_scale))
    panel_height = line_height * (len(entries) + 1) + 10
    panel_width = min(image.shape[1], max(390, int(image.shape[1] * 0.55)))
    panel_top = max(0, image.shape[0] - panel_height)
    overlay = image.copy()
    cv2.rectangle(overlay, (0, panel_top), (panel_width, image.shape[0]), BACKGROUND_COLOR, -1)
    cv2.addWeighted(overlay, 0.78, image, 0.22, 0, image)
    cv2.putText(
        image,
        "Full screenshot replay",
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


def _annotate(image: np.ndarray, detection: DescrDetection, anchor: tuple[int, int]) -> np.ndarray:
    annotated = image.copy()
    if detection.rarity_match is not None:
        _draw_match(annotated, "rarity", detection.rarity_match, RAW_MATCH_COLOR)
    if detection.separator_match is not None:
        _draw_match(annotated, "separator", detection.separator_match, SEPARATOR_MATCH_COLOR)
    if detection.bottom_match is not None:
        _draw_match(annotated, "bottom", detection.bottom_match, BOTTOM_MATCH_COLOR)

    if detection.crop_roi is not None:
        x, y, width, height = detection.crop_roi
        cv2.rectangle(annotated, (x, y), (x + width, y + height), CROP_COLOR, 4)
        cv2.putText(
            annotated,
            "cropped tooltip region",
            (max(0, x), max(18, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            _font_scale(annotated),
            CROP_COLOR,
            2,
            cv2.LINE_AA,
        )

    cv2.drawMarker(annotated, anchor, ANCHOR_COLOR, cv2.MARKER_CROSS, 36, 3)
    if not detection.found:
        reason = detection.failure_reason or "unknown failure"
        cv2.rectangle(annotated, (0, 0), (annotated.shape[1] - 1, 40), FAILURE_COLOR, -1)
        cv2.putText(
            annotated,
            f"FAILURE: {reason.replace('_', ' ')}",
            (8, 29),
            cv2.FONT_HERSHEY_SIMPLEX,
            _font_scale(annotated),
            TEXT_COLOR,
            2,
            cv2.LINE_AA,
        )
    _draw_legend(annotated)
    return annotated


def show_result(image: np.ndarray) -> None:
    """Display the full replay result until the user closes the blocking window."""
    cv2.imshow("D4LF full screenshot replay", image)
    cv2.waitKey(0)
    cv2.destroyWindow("D4LF full screenshot replay")


def _write_image(path: Path, image: np.ndarray) -> None:
    if not cv2.imwrite(str(path), image):
        message = f"Could not write replay output: {path}"
        raise OSError(message)


def _has_valid_crop(image: np.ndarray, detection: DescrDetection) -> bool:
    if detection.cropped_descr is None or detection.crop_roi is None:
        return False
    x, y, width, height = detection.crop_roi
    return (
        x >= 0
        and y >= 0
        and width > 0
        and height > 0
        and x + width <= image.shape[1]
        and y + height <= image.shape[0]
        and detection.cropped_descr.shape[:2] == (height, width)
    )


def run_replay(config: ReplayConfig, *, display: bool = True) -> ReplayResult:
    """Detect an item tooltip in a full screenshot and save the resulting crop."""
    image_path, image = validate_replay_config(config)
    output_path = image_path.with_name(f"{image_path.stem}_full_template_matches.png")
    crop_path = image_path.with_name(f"{image_path.stem}_cropped.png")
    width, height = _parse_resolution(config.game_resolution)
    LOGGER.info(
        "Full replay inputs: image=%s resolution=%sx%s item_anchor=%s", image_path, width, height, config.item_anchor
    )

    resolution_manager = ResManager()
    previous_resolution = "x".join(str(value) for value in resolution_manager.resolution)
    try:
        resolution_manager.set_resolution(config.game_resolution)
        detection = find_descr_with_diagnostics(image, tuple(config.item_anchor))
    finally:
        resolution_manager.set_resolution(previous_resolution)
    _log_detection(detection)

    if not detection.found:
        annotated = _annotate(image, detection, tuple(config.item_anchor))
        _write_image(output_path, annotated)
        LOGGER.info("Full replay output: %s", output_path)
        if display:
            show_result(annotated)
        return ReplayResult(
            output_path=output_path, crop_path=None, found=False, failure_reason=detection.failure_reason
        )

    if not _has_valid_crop(image, detection):
        detection = DescrDetection(
            found=False,
            rarity=detection.rarity,
            crop_roi=detection.crop_roi,
            rarity_match=detection.rarity_match,
            separator_match=detection.separator_match,
            bottom_match=detection.bottom_match,
            failure_reason="invalid_crop",
        )
        _log_detection(detection)
        annotated = _annotate(image, detection, tuple(config.item_anchor))
        _write_image(output_path, annotated)
        if display:
            show_result(annotated)
        return ReplayResult(
            output_path=output_path, crop_path=None, found=False, failure_reason=detection.failure_reason
        )

    _write_image(crop_path, detection.cropped_descr)
    annotated = _annotate(image, detection, tuple(config.item_anchor))
    _write_image(output_path, annotated)
    LOGGER.info(
        "Full replay output: %s crop=%s found=%s failure_reason=%s",
        output_path,
        crop_path,
        detection.found,
        detection.failure_reason,
    )
    if display:
        show_result(annotated)
    return ReplayResult(output_path=output_path, crop_path=crop_path, found=True, failure_reason=None)


def main() -> int:
    setup(enable_stdout=True)
    try:
        result = run_replay(REPLAY_CONFIG)
    except ReplayConfigurationError as error:
        LOGGER.error("Replay configuration error: %s", error)
        return 2
    return 0 if result.found else 1


if __name__ == "__main__":
    raise SystemExit(main())
