"""Compatibility exports for matching primitives."""

from typing import TYPE_CHECKING

from src.perception.screenshot import screenshot

from .matcher import get_cv_result as _get_cv_result
from .resources import process_template_refs

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy as np

    from src.settings import Template


def get_cv_result(
    template: Template,
    inp_img: np.ndarray,
    roi: Sequence[int | float] | None = None,
    color_match: list[np.ndarray] | None = None,
    use_grayscale: bool = False,
    take_debug_screenshot: bool = False,
) -> tuple[np.ndarray | None, np.ndarray, list[int]]:
    """Run the pure matcher and optionally retain the legacy debug screenshot behavior."""
    result = _get_cv_result(template, inp_img, roi, color_match, use_grayscale)
    if take_debug_screenshot:
        _, _, resolved_roi = result
        rx, ry, rw, rh = resolved_roi
        screenshot("template_finder", img=inp_img[ry : ry + rh, rx : rx + rw])
    return result


__all__ = ["get_cv_result", "process_template_refs"]
