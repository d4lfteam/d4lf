import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import cv2

from src.perception import TemplateMatch, search
from src.tools.replay.common import draw_legend, game_resolution, load_replay_image, run_replay_main, save_replay_output
from src.tools.replay.common import font_scale as _font_scale
from src.tools.replay.common import parse_resolution as _parse_resolution
from src.tools.replay.common import raise_configuration_error as _raise_configuration_error

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy as np


LOGGER = logging.getLogger("d4lf")

MATCH_COLOR = (0, 255, 255)

TEMPLATES = [
    x.stem for x in (Path(__file__).parents[3] / "assets/templates/item_descr").glob("*.png") if "item_top" in x.stem
]


@dataclass
class ReplayConfig:
    game_resolution: str
    image_path: Path | str
    templates: Sequence[str | int]
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
    image_path=Path(r"/Users/chris/Downloads/asd.png"),
    templates=TEMPLATES.copy(),
    threshold=0.8,
    game_resolution="3840x2160",
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
    entries = [
        (None, f"Templates: {template_count}"),
        (None, f"Minimum confidence: {threshold:.2f}"),
        (None, f"Matches: {match_count}"),
    ]
    draw_legend(image, "Template matching replay", entries, min_width=430, width_ratio=0.65)


def _annotate(image: np.ndarray, matches: list[TemplateMatch], template_count: int, threshold: float) -> np.ndarray:
    annotated = image.copy()
    for match in matches:
        _draw_match(annotated, match)
    _draw_legend(annotated, template_count, threshold, len(matches))
    return annotated


def run_replay(config: ReplayConfig, *, display: bool = True) -> ReplayResult:
    """Match every configured template against a screen and save an annotated copy."""
    image_path, image = validate_replay_config(config)
    templates = [template for template in config.templates if isinstance(template, str)]
    LOGGER.info(
        "Template matching inputs: image=%s resolution=%s templates=%s threshold=%.4f",
        image_path,
        config.game_resolution,
        templates,
        config.threshold,
    )
    with game_resolution(config.game_resolution):
        search_result = search(
            templates, inp_img=image, threshold=config.threshold, use_grayscale=True, mode="all", do_multi_process=False
        )
    matches = search_result.matches
    _log_matches(matches)

    output_path = image_path.with_name(f"{image_path.stem}_all_template_matches.png")
    annotated = _annotate(image, matches, len(templates), config.threshold)
    LOGGER.info("Template matching output: %s", output_path)
    save_replay_output(output_path, annotated, window_name="D4LF template matching replay", display=display)
    return ReplayResult(output_path=output_path, matches=matches)


def main() -> int:
    return run_replay_main(lambda: run_replay(REPLAY_CONFIG).found)


if __name__ == "__main__":
    raise SystemExit(main())
