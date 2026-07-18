"""Shared validation and output helpers for the replay tools."""

import re
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import cv2

if TYPE_CHECKING:
    import numpy as np


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
    return max(0.45, min(1.0, image.shape[0] / 800))


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
