"""Resolve template and UI resource references used by matching."""

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

import cv2
import numpy as np

from src.perception.image import alpha_to_mask, color_filter
from src.settings import Template, get_ui_coordinates

if TYPE_CHECKING:
    from .models import ColorMatch, TemplateReference, TemplateReferences

LOGGER = logging.getLogger(__name__)


def process_template_refs(ref: TemplateReferences) -> list[Template]:
    """Turn named or inline template references into loaded templates."""
    templates: list[Template] = []
    refs: list[TemplateReference] = [ref] if isinstance(ref, (str, np.ndarray)) else list(ref)
    for template_ref in refs:
        if isinstance(template_ref, str):
            try:
                templates.append(get_ui_coordinates().templates[template_ref.lower()])
            except KeyError:
                LOGGER.warning(f"Template not defined: {template_ref}")
        elif isinstance(template_ref, np.ndarray):
            template = Template(img_bgr=template_ref, img_gray=cv2.cvtColor(template_ref, cv2.COLOR_BGR2GRAY))
            alpha_mask = alpha_to_mask(template_ref)
            if alpha_mask is not None:
                template.alpha_mask = alpha_mask
            templates.append(template)
    return templates


def _as_finite_array(value: object, size: int) -> np.ndarray | None:
    if not isinstance(value, (np.ndarray, Sequence)) or isinstance(value, (str, bytes)):
        return None
    try:
        array = np.asarray(value)
    except TypeError, ValueError:
        return None
    if array.ndim != 1 or array.size != size:
        return None
    if not np.issubdtype(array.dtype, np.number) or np.issubdtype(array.dtype, np.complexfloating):
        return None
    return array if bool(np.all(np.isfinite(array))) else None


def _validate_roi(value: object, *, label: str = "roi") -> list[float]:
    array = _as_finite_array(value, 4)
    if array is None:
        message = f"Invalid {label} value"
        raise ValueError(message)
    values = [float(item) for item in array]
    if values[0] < 0 or values[1] < 0 or values[2] <= 0 or values[3] <= 0:
        message = f"Invalid {label} value"
        raise ValueError(message)
    return values


def resolve_roi(roi: Sequence[int | float] | str | None) -> list[float] | None:
    """Resolve an inline or named region of interest into numeric coordinates."""
    if roi is None:
        return None
    if not isinstance(roi, str):
        return _validate_roi(roi)
    try:
        candidate_roi = getattr(get_ui_coordinates().roi, roi)
    except (AttributeError, KeyError, TypeError) as error:
        LOGGER.error(f"Invalid roi key: {roi}")
        LOGGER.error(error)
        message = f"Invalid roi key: {roi}"
        raise ValueError(message) from error
    try:
        return _validate_roi(candidate_roi, label=f"roi value for key: {roi}")
    except ValueError as error:
        message = f"Invalid roi value for key: {roi}"
        raise ValueError(message) from error


def _validate_hsv_range(lower: object, upper: object, *, label: str) -> list[np.ndarray]:
    lower_array = _as_finite_array(lower, 3)
    upper_array = _as_finite_array(upper, 3)
    if lower_array is None or upper_array is None:
        message = f"Invalid color range for {label}"
        raise ValueError(message)
    lower_values = [float(item) for item in lower_array]
    upper_values = [float(item) for item in upper_array]
    if not (
        -179 <= lower_values[0] <= 179
        and -179 <= upper_values[0] <= 179
        and all(0 <= item <= 255 for item in (*lower_values[1:], *upper_values[1:]))
        and all(lower <= upper for lower, upper in zip(lower_values, upper_values, strict=True))
    ):
        message = f"Invalid color range for {label}"
        raise ValueError(message)
    return [lower_array, upper_array]


def resolve_color_match(color_match: ColorMatch) -> list[np.ndarray] | None:
    """Resolve a named or inline HSV range into lower and upper arrays."""
    if color_match is None:
        return None
    if isinstance(color_match, str):
        try:
            candidate_color = getattr(get_ui_coordinates().colors, color_match)
            lower = candidate_color.h_s_v_min
            upper = candidate_color.h_s_v_max
        except (AttributeError, KeyError, TypeError) as error:
            LOGGER.error(f"Invalid color_match key: {color_match}")
            LOGGER.error(error)
            message = f"Invalid color_match key: {color_match}"
            raise ValueError(message) from error
        try:
            return _validate_hsv_range(lower, upper, label=f"key: {color_match}")
        except ValueError as error:
            message = f"Invalid color range for key: {color_match}"
            raise ValueError(message) from error
    if not isinstance(color_match, Sequence) or len(color_match) != 2:
        message = "Invalid color range"
        raise ValueError(message)
    return _validate_hsv_range(color_match[0], color_match[1], label="value")


def apply_color_filter(image: np.ndarray, color_match: list[np.ndarray]) -> np.ndarray:
    """Apply a resolved color range, raising a useful error for unusable output."""
    _, filtered_image = color_filter(image, color_match)
    if filtered_image is None:
        message = "Color filtering did not produce an image"
        raise RuntimeError(message)
    return filtered_image
