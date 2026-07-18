from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import cv2
import numpy as np

from src.settings import Template, get_ui_coordinates

from ._image import alpha_to_mask, color_filter

LOGGER = logging.getLogger(__name__)
_MISSING_BGR_IMAGE = "Template has no BGR image"
_MISSING_GRAYSCALE_IMAGE = "Template has no grayscale image"
_INVALID_COLOR_IMAGE = "Color filtering did not produce an image"

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ._matching_models import TemplateReference, TemplateReferences


def process_template_refs(ref: TemplateReferences) -> list[Template]:
    templates = []
    refs: list[TemplateReference] = [ref] if isinstance(ref, (str, np.ndarray)) else list(ref)
    for i in refs:
        if isinstance(i, str):
            try:
                templates.append(get_ui_coordinates().templates[i.lower()])
            except KeyError:
                LOGGER.warning(f"Template not defined: {i}")
        elif isinstance(i, np.ndarray):
            template = Template(img_bgr=i, img_gray=cv2.cvtColor(i, cv2.COLOR_BGR2GRAY))
            alpha_mask = alpha_to_mask(i)
            if alpha_mask is not None:
                template.alpha_mask = alpha_mask
            templates.append(template)
    return templates


def get_cv_result(
    template: Template,
    inp_img: np.ndarray,
    roi: Sequence[int | float] | None = None,
    color_match: list[np.ndarray] | None = None,
    use_grayscale: bool = False,
    take_debug_screenshot: bool = False,
) -> tuple[np.ndarray | None, np.ndarray, list[int]]:
    template_bgr = template.img_bgr
    if not isinstance(template_bgr, np.ndarray):
        raise RuntimeError(_MISSING_BGR_IMAGE)

    resolved_roi = [0, 0, inp_img.shape[1], inp_img.shape[0]] if roi is None else [max(0, int(value)) for value in roi]
    rx, ry, rw, rh = resolved_roi
    img = inp_img[ry : ry + rh, rx : rx + rw]
    if img.shape[0] == 0 or img.shape[1] == 0:
        return None, template_bgr, resolved_roi
    if take_debug_screenshot:
        from src.perception import screenshot  # ruff:ignore[import-outside-top-level]

        screenshot("template_finder", img=img)

    if color_match:
        _, filtered_template = color_filter(template_bgr, color_match)
        _, filtered_img = color_filter(img, color_match)
        if filtered_template is None or filtered_img is None:
            raise RuntimeError(_INVALID_COLOR_IMAGE)
        template_img = filtered_template
        img = filtered_img
    elif use_grayscale:
        template_img = template.img_gray
        if not isinstance(template_img, np.ndarray):
            raise RuntimeError(_MISSING_GRAYSCALE_IMAGE)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        template_img = template_bgr
    if not (img.shape[0] > template_img.shape[0] and img.shape[1] > template_img.shape[1]):
        res = None
    else:
        res = cv2.matchTemplate(img, template_img, cv2.TM_CCOEFF_NORMED, mask=template.alpha_mask)
        np.nan_to_num(res, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    return res, template_img, resolved_roi
