"""Shared validation and output helpers for the replay tools."""

import re
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import cv2

from src.settings import get_ui_coordinates

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    import numpy as np


PANEL_BACKGROUND_COLOR = (30, 30, 30)
LEGEND_TEXT_COLOR = (255, 255, 255)


class ReplayConfigurationError(ValueError):
    """Raised when an editable replay configuration cannot be used."""


def raise_configuration_error(message: str) -> NoReturn:
    """Raise the common replay configuration error with ``message``."""
    raise ReplayConfigurationError(message)


def parse_resolution(resolution: str) -> tuple[int, int]:
    """Parse a game resolution written as ``WIDTHxHEIGHT``."""
    if not isinstance(resolution, str) or re.fullmatch(r"[1-9]\d*x[1-9]\d*", resolution) is None:
        raise_configuration_error(f"Game resolution must use WIDTHxHEIGHT form, got {resolution!r}.")
    width, height = (int(value) for value in resolution.split("x"))
    return width, height


def load_replay_image(image_path: Path | str, *, label: str) -> tuple[Path, np.ndarray]:
    """Validate and decode a replay image, using ``label`` in error messages."""
    try:
        normalized_path = Path(image_path)
    except TypeError:
        raise_configuration_error(f"{label} path is invalid: {image_path!r}")
    if not normalized_path.exists():
        raise_configuration_error(f"{label} path does not exist: {normalized_path}")
    if not normalized_path.is_file():
        raise_configuration_error(f"{label} path is not a file: {normalized_path}")
    image = cv2.imread(str(normalized_path), cv2.IMREAD_COLOR)
    if image is None:
        raise_configuration_error(f"{label} cannot be read: {normalized_path}")
    return normalized_path, image


def font_scale(image: np.ndarray) -> float:
    """Return a readable annotation font scale for an image's height."""
    height = int(image.shape[0])
    return max(0.45, min(1.0, height / 800))


def show_replay_result(image: np.ndarray, window_name: str) -> None:
    """Display a replay result until the user closes its blocking window."""
    cv2.imshow(window_name, image)
    cv2.waitKey(0)
    cv2.destroyWindow(window_name)


def write_image(path: Path, image: np.ndarray) -> None:
    """Write a replay image and raise a useful error when OpenCV cannot do so."""
    if not cv2.imwrite(str(path), image):
        message = f"Could not write replay output: {path}"
        raise OSError(message)


@contextmanager
def game_resolution(resolution: str) -> Generator[None]:
    """Temporarily switch the UI coordinates to ``resolution``, restoring the previous one on exit."""
    resolution_manager = get_ui_coordinates()
    previous_resolution = "x".join(str(value) for value in resolution_manager.resolution)
    try:
        resolution_manager.set_resolution(resolution)
        yield
    finally:
        resolution_manager.set_resolution(previous_resolution)


def draw_legend(
    image: np.ndarray,
    title: str,
    entries: Sequence[tuple[tuple[int, int, int] | None, str]],
    *,
    min_width: int,
    width_ratio: float,
) -> None:
    """Draw a translucent bottom legend panel with a title and rows, each with an optional color swatch."""
    scale = font_scale(image)
    line_height = max(20, int(25 * scale))
    panel_height = line_height * (len(entries) + 1) + 10
    panel_width = min(image.shape[1], max(min_width, int(image.shape[1] * width_ratio)))
    panel_top = max(0, int(image.shape[0]) - panel_height)
    overlay = image.copy()
    cv2.rectangle(overlay, (0, panel_top), (panel_width, image.shape[0]), PANEL_BACKGROUND_COLOR, -1)
    cv2.addWeighted(overlay, 0.78, image, 0.22, 0, image)
    cv2.putText(image, title, (8, panel_top + line_height), cv2.FONT_HERSHEY_SIMPLEX, scale, LEGEND_TEXT_COLOR, 1)
    for row, (color, label) in enumerate(entries, start=1):
        y = panel_top + line_height * (row + 1) - 5
        label_x = 8
        if color is not None:
            cv2.rectangle(image, (8, y - line_height + 5), (24, y + 2), color, -1)
            label_x = 32
        cv2.putText(image, label, (label_x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, LEGEND_TEXT_COLOR, 1)
