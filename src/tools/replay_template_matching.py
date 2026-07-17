import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import cv2

from src.config.ui import ResManager
from src.logger import setup
from src.template_finder import TemplateMatch, search
from src.tools.replay_common import ReplayConfigurationError, load_replay_image, show_replay_result
from src.tools.replay_common import font_scale as _font_scale
from src.tools.replay_common import parse_resolution as _parse_resolution
from src.tools.replay_common import raise_configuration_error as _raise_configuration_error
from src.tools.replay_common import write_image as _write_image

if TYPE_CHECKING:
    import numpy as np


LOGGER = logging.getLogger("d4lf")

MATCH_COLOR = (0, 255, 255)
TEXT_COLOR = (255, 255, 255)
BACKGROUND_COLOR = (30, 30, 30)

TEMPLATES = [
    x.stem for x in (Path(__file__).parents[2] / "assets/templates/item_descr").glob("*.png") if "seal" in x.stem
]


@dataclass
class ReplayConfig:
    game_resolution: str
    image_path: Path | str
    templates: list[str]
    threshold: float


@dataclass(frozen=True)
class ReplayResult:
    output_path: Path
    matches: list[TemplateMatch]

    @property
    def found(self) -> bool:
        return bool(self.matches)


# BEGIN EDITABLE REPLAY CONFIGURATION
# Replace the screenshot path, template names, and minimum confidence as needed.
REPLAY_CONFIG = ReplayConfig(
    image_path=Path(r"E:\Downloads\test5.png"), templates=TEMPLATES.copy(), threshold=0.75, game_resolution="3840x2160"
)
# END EDITABLE REPLAY CONFIGURATION


def validate_replay_config(config: ReplayConfig) -> tuple[Path, np.ndarray]:
    """Validate replay inputs and return the normalized image path and decoded image."""
    image_path, image = load_replay_image(config.image_path, label="Screen image")

    if not isinstance(config.templates, list) or not config.templates:
        _raise_configuration_error("Templates must be a non-empty list of template names.")
    if any(not isinstance(template, str) or not template for template in config.templates):
        _raise_configuration_error("Every template must be a non-empty string.")
    if (
        isinstance(config.threshold, bool)
        or not isinstance(config.threshold, (int, float))
        or not 0 <= config.threshold <= 1
    ):
        _raise_configuration_error("Minimum threshold must be a number between 0 and 1.")
    _parse_resolution(config.game_resolution)
    return image_path, image


def _log_matches(matches: list[TemplateMatch]) -> None:
    LOGGER.info("Template matching: count=%d", len(matches))
    for match in matches:
        LOGGER.info(
            "Template match: template=%s center=%s region=%s confidence=%.4f",
            match.name,
            match.center,
            match.region,
            match.score,
        )


def _draw_match(image: np.ndarray, match: TemplateMatch) -> None:
    x, y, width, height = match.region
    font_scale = _font_scale(image)
    cv2.rectangle(image, (x, y), (x + width, y + height), MATCH_COLOR, 3)
    cv2.putText(
        image,
        f"{match.name} ({match.score:.2f})",
        (max(0, x), max(18, y - 6)),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        MATCH_COLOR,
        2,
        cv2.LINE_AA,
    )


def _draw_legend(image: np.ndarray, template_count: int, threshold: float, match_count: int) -> None:
    font_scale = _font_scale(image)
    line_height = max(20, int(25 * font_scale))
    panel_height = line_height * 4 + 10
    panel_width = min(image.shape[1], max(430, int(image.shape[1] * 0.65)))
    panel_top = max(0, image.shape[0] - panel_height)
    overlay = image.copy()
    cv2.rectangle(overlay, (0, panel_top), (panel_width, image.shape[0]), BACKGROUND_COLOR, -1)
    cv2.addWeighted(overlay, 0.78, image, 0.22, 0, image)
    lines = (
        "Template matching replay",
        f"Templates: {template_count}",
        f"Minimum confidence: {threshold:.2f}",
        f"Matches: {match_count}",
    )
    for row, label in enumerate(lines):
        y = panel_top + line_height * (row + 1) - 5
        cv2.putText(image, label, (8, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, TEXT_COLOR, 1, cv2.LINE_AA)


def _annotate(image: np.ndarray, matches: list[TemplateMatch], template_count: int, threshold: float) -> np.ndarray:
    annotated = image.copy()
    for match in matches:
        _draw_match(annotated, match)
    _draw_legend(annotated, template_count, threshold, len(matches))
    return annotated


def show_result(image: np.ndarray) -> None:
    """Display the matching result until the user closes the blocking window."""
    show_replay_result(image, "D4LF template matching replay")


def run_replay(config: ReplayConfig, *, display: bool = True) -> ReplayResult:
    """Match every configured template against a screen and save an annotated copy."""
    image_path, image = validate_replay_config(config)
    LOGGER.info(
        "Template matching inputs: image=%s resolution=%s templates=%s threshold=%.4f",
        image_path,
        config.game_resolution,
        config.templates,
        config.threshold,
    )
    resolution_manager = ResManager()
    previous_resolution = "x".join(str(value) for value in resolution_manager.resolution)
    try:
        resolution_manager.set_resolution(config.game_resolution)
        search_result = search(
            config.templates,
            inp_img=image,
            threshold=config.threshold,
            use_grayscale=True,
            mode="all",
            do_multi_process=False,
        )
    finally:
        resolution_manager.set_resolution(previous_resolution)
    matches = search_result.matches
    _log_matches(matches)

    output_path = image_path.with_name(f"{image_path.stem}_all_template_matches.png")
    annotated = _annotate(image, matches, len(config.templates), config.threshold)
    _write_image(output_path, annotated)
    LOGGER.info("Template matching output: %s", output_path)
    if display:
        show_result(annotated)
    return ReplayResult(output_path=output_path, matches=matches)


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
