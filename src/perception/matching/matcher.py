"""Pure OpenCV template matching operations."""

from typing import TYPE_CHECKING

import cv2
import numpy as np

from src.perception.matching.models import ImageMatch
from src.perception.matching.resources import apply_color_filter

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from src.settings import Template

_MISSING_BGR_IMAGE = "Template has no BGR image"
_MISSING_GRAYSCALE_IMAGE = "Template has no grayscale image"


def get_cv_result(
    template: Template,
    inp_img: np.ndarray,
    roi: Sequence[int | float] | None = None,
    color_match: list[np.ndarray] | None = None,
    use_grayscale: bool = False,
) -> tuple[np.ndarray | None, np.ndarray, list[int]]:
    """Prepare an image and return OpenCV's correlation matrix.

    This function only reads its inputs and performs image operations. In particular, it does
    not capture a frame, access monitor coordinates, or write debug screenshots.
    """
    template_bgr = template.img_bgr
    if not isinstance(template_bgr, np.ndarray):
        raise RuntimeError(_MISSING_BGR_IMAGE)

    resolved_roi = [0, 0, inp_img.shape[1], inp_img.shape[0]] if roi is None else [max(0, int(value)) for value in roi]
    rx, ry, rw, rh = resolved_roi
    img = inp_img[ry : ry + rh, rx : rx + rw]
    if img.shape[0] == 0 or img.shape[1] == 0:
        return None, template_bgr, resolved_roi
    if color_match:
        template_img = apply_color_filter(template_bgr, color_match)
        img = apply_color_filter(img, color_match)
    elif use_grayscale:
        template_img = template.img_gray
        if not isinstance(template_img, np.ndarray):
            raise RuntimeError(_MISSING_GRAYSCALE_IMAGE)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        template_img = template_bgr
    if not (img.shape[0] > template_img.shape[0] and img.shape[1] > template_img.shape[1]):
        result = None
    else:
        result = cv2.matchTemplate(img, template_img, cv2.TM_CCOEFF_NORMED, mask=template.alpha_mask)
        np.nan_to_num(result, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    return result, template_img, resolved_roi


def find_image_matches(
    template: Template,
    inp_img: np.ndarray,
    roi: Sequence[int | float] | None,
    color_match: list[np.ndarray] | None,
    use_grayscale: bool,
    threshold: float,
    get_result: Callable[..., tuple[np.ndarray | None, np.ndarray, list[int]]] = get_cv_result,
) -> list[ImageMatch]:
    """Find all non-overlapping matches for one template in image coordinates."""
    res, template_img, resolved_roi = get_result(template, inp_img, roi, color_match, use_grayscale)
    matches: list[ImageMatch] = []
    while res is not None:
        _, max_value, _, max_position = cv2.minMaxLoc(res)
        if max_value < threshold:
            break
        region = (
            int(max_position[0] + resolved_roi[0]),
            int(max_position[1] + resolved_roi[1]),
            int(template_img.shape[1]),
            int(template_img.shape[0]),
        )
        matches.append(ImageMatch(region=region, score=float(max_value)))
        cv2.rectangle(
            res,
            (max_position[0] - template_img.shape[1] // 2, max_position[1] - template_img.shape[0] // 2),
            (max_position[0] + template_img.shape[1], max_position[1] + template_img.shape[0]),
            (0, 0, 0),
            -1,
        )
    return matches
