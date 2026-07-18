from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import FIRST_COMPLETED, wait
from typing import TYPE_CHECKING

import cv2
import numpy as np

from src import TP
from src.settings import Template, get_ui_coordinates

from ._capture import Cam
from ._matching_core import get_cv_result, process_template_refs
from ._matching_models import ColorMatch, SearchResult, TemplateMatch, TemplateReferences
from ._roi import get_center

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

LOGGER = logging.getLogger(__name__)

TEMPLATES_LOCK = threading.Lock()


def _is_finite_real_array(value: object, size: int) -> bool:
    if not isinstance(value, np.ndarray) or value.ndim != 1 or value.size != size:
        return False
    if not np.issubdtype(value.dtype, np.number) or np.issubdtype(value.dtype, np.complexfloating):
        return False
    return bool(np.all(np.isfinite(value)))


def _is_valid_roi(value: np.ndarray) -> bool:
    values = [float(item) for item in value]
    return values[0] >= 0 and values[1] >= 0 and values[2] > 0 and values[3] > 0


def _is_valid_hsv_range(lower: np.ndarray, upper: np.ndarray) -> bool:
    lower_values = [float(item) for item in lower]
    upper_values = [float(item) for item in upper]
    return (
        -179 <= lower_values[0] <= 179
        and -179 <= upper_values[0] <= 179
        and all(0 <= item <= 255 for item in (*lower_values[1:], *upper_values[1:]))
        and all(lower_value <= upper_value for lower_value, upper_value in zip(lower_values, upper_values, strict=True))
    )


_process_template_refs = process_template_refs
_get_cv_result = get_cv_result


def _find_template_matches(
    template: Template,
    img: np.ndarray,
    roi: list[float] | None,
    color_match: list[np.ndarray] | None,
    use_grayscale: bool,
    threshold: float,
    take_debug_screenshot: bool = False,
) -> list[TemplateMatch]:
    """Find all matches for one template without sharing search state between workers."""
    res, template_img, new_roi = _get_cv_result(template, img, roi, color_match, use_grayscale, take_debug_screenshot)
    template_matches = []

    while res is not None:
        _, max_val, _, max_pos = cv2.minMaxLoc(res)
        if max_val < threshold:
            break

        rec_x = int(max_pos[0] + new_roi[0])
        rec_y = int(max_pos[1] + new_roi[1])
        rec_w = int(template_img.shape[1])
        rec_h = int(template_img.shape[0])

        region = (rec_x, rec_y, rec_w, rec_h)
        center = get_center(region)
        template_match = TemplateMatch(
            region=list(region),
            region_monitor=[*Cam().window_to_monitor((rec_x, rec_y)), rec_w, rec_h],
            center=center,
            center_monitor=Cam().window_to_monitor(center),
            name=template.name,
            score=max_val,
        )
        template_matches.append(template_match)

        cv2.rectangle(
            res,
            (max_pos[0] - template_img.shape[1] // 2, max_pos[1] - template_img.shape[0] // 2),
            (max_pos[0] + template_img.shape[1], max_pos[1] + template_img.shape[0]),
            (0, 0, 0),
            -1,
        )

    return template_matches


def search(
    ref: TemplateReferences,
    inp_img: np.ndarray | None = None,
    threshold: float = 0.7,
    roi: Sequence[int | float] | str | None = None,
    use_grayscale: bool = False,
    color_match: ColorMatch = None,
    mode: str = "first",
    timeout: int = 0,
    suppress_debug: bool = True,
    do_multi_process: bool = True,
    take_debug_screenshot: bool = False,
    stop_condition: Callable[[list[TemplateMatch]], bool] | None = None,
) -> SearchResult:
    """Search for templates in an image.

    :param ref: Either key of a already loaded template, list of such keys, or a image which is used as template
    :param inp_img: Image in which the template will be searched
    :param threshold: Threshold which determines if a template is found or not
    :param roi: Region of Interest of the inp_img to restrict search area. Format [left, top, width, height] or string corresponding to a key in Config().ui_roi
    :param use_grayscale: Use grayscale template matching for speed up
    :param color_match: Pass a color to be used by misc.color_filter to filter both image of interest and template image (format Config().colors["color"]) or string corresponding to a key in Config().colors
    :param mode: search "first" match or "all" matches
    :param timeout: wait for the specified number of seconds before stopping search
    :param do_multi_process: flag if multi process should be used in case there are multiple refs
    :param stop_condition: Optional predicate for ending an "all" search early once enough matches are collected.
    :return: SearchResult object containing success and matches
    """
    templates = _process_template_refs(ref)
    result = SearchResult()
    matches = []
    future_list = []
    resolved_roi: list[float] | None
    if isinstance(roi, str):
        try:
            candidate_roi = getattr(get_ui_coordinates().roi, roi)
        except (AttributeError, KeyError, TypeError) as e:
            LOGGER.error(f"Invalid roi key: {roi}")
            LOGGER.error(e)
            message = f"Invalid roi key: {roi}"
            raise ValueError(message) from e
        if not _is_finite_real_array(candidate_roi, 4) or not _is_valid_roi(candidate_roi):
            message = f"Invalid roi value for key: {roi}"
            raise ValueError(message)
        resolved_roi = [float(value) for value in candidate_roi]
    else:
        resolved_roi = None if roi is None else [float(value) for value in roi]

    resolved_color_match: list[np.ndarray] | None
    if isinstance(color_match, str):
        try:
            candidate_color = getattr(get_ui_coordinates().colors, color_match)
            lower = candidate_color.h_s_v_min
            upper = candidate_color.h_s_v_max
        except (AttributeError, KeyError, TypeError) as e:
            LOGGER.error(f"Invalid color_match key: {color_match}")
            LOGGER.error(e)
            message = f"Invalid color_match key: {color_match}"
            raise ValueError(message) from e
        if not _is_finite_real_array(lower, 3) or not _is_finite_real_array(upper, 3):
            message = f"Invalid color range for key: {color_match}"
            raise ValueError(message)
        if not isinstance(lower, np.ndarray) or not isinstance(upper, np.ndarray):
            message = f"Invalid color range for key: {color_match}"
            raise ValueError(message)
        if not _is_valid_hsv_range(lower, upper):
            message = f"Invalid color range for key: {color_match}"
            raise ValueError(message)
        resolved_color_match = [lower, upper]
    else:
        resolved_color_match = color_match

    stop_search = threading.Event()

    def should_stop() -> bool:
        return bool((matches and mode == "first") or (stop_condition is not None and stop_condition(matches)))

    def _process_cv_result(template: Template, img: np.ndarray, take_debug_screenshot: bool = False) -> bool:
        new_match = False
        res, template_img, new_roi = _get_cv_result(
            template, img, resolved_roi, resolved_color_match, use_grayscale, take_debug_screenshot
        )

        while not stop_search.is_set() and not should_stop() and res is not None:
            _, max_val, _, max_pos = cv2.minMaxLoc(res)

            if max_val >= threshold:
                new_match = True
                # Save rectangle corresponding to the matched region
                rec_x = int(max_pos[0] + new_roi[0])
                rec_y = int(max_pos[1] + new_roi[1])
                rec_w = int(template_img.shape[1])
                rec_h = int(template_img.shape[0])

                region = (rec_x, rec_y, rec_w, rec_h)
                center = get_center(region)
                template_match = TemplateMatch(
                    region=list(region),
                    region_monitor=[*Cam().window_to_monitor((rec_x, rec_y)), rec_w, rec_h],
                    center=center,
                    center_monitor=Cam().window_to_monitor(center),
                    name=template.name,
                    score=max_val,
                )

                matches.append(template_match)
                if should_stop():
                    stop_search.set()
                    break
                # Remove the matched region from the result
                cv2.rectangle(
                    res,
                    (max_pos[0] - template_img.shape[1] // 2, max_pos[1] - template_img.shape[0] // 2),
                    (max_pos[0] + template_img.shape[1], max_pos[1] + template_img.shape[0]),
                    (0, 0, 0),
                    -1,
                )
                # result_norm = cv2.normalize(res, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                # cv2.imwrite(f"res{i}.png", result_norm)
                # i += 1
            else:
                break
        return new_match

    start = time.time()
    time_remains = True
    while time_remains and not matches:
        img = Cam().grab() if inp_img is None else inp_img
        if do_multi_process:
            if stop_condition is not None:
                # Worker completion order is nondeterministic. Collect each worker's local results first, then
                # apply the stop condition in template order so a lower-scoring template cannot win the race.
                future_list = [
                    TP.submit(
                        _find_template_matches,
                        template,
                        img,
                        resolved_roi,
                        resolved_color_match,
                        use_grayscale,
                        threshold,
                        take_debug_screenshot,
                    )
                    for template in templates
                ]
                template_matches = [future.result() for future in future_list]
                for matches_for_template in template_matches:
                    for template_match in matches_for_template:
                        matches.append(template_match)
                        if should_stop():
                            stop_search.set()
                            break
                    if stop_search.is_set():
                        break
            elif mode == "first":
                future_list = [
                    TP.submit(_process_cv_result, template, img, take_debug_screenshot) for template in templates
                ]
                pending = set(future_list)
                while pending and not should_stop():
                    done, pending = wait(pending, return_when=FIRST_COMPLETED)
                    for future in done:
                        _ = future.result()
                for future in pending:
                    future.cancel()
            else:
                future_list = [
                    TP.submit(_process_cv_result, template, img, take_debug_screenshot) for template in templates
                ]
                for future in future_list:
                    _ = future.result()
        else:
            for template in templates:
                res = _process_cv_result(template, img, take_debug_screenshot)
                if stop_search.is_set() or (mode == "first" and res):
                    break

        time_remains = time.time() - start < timeout

    if matches:
        result.success = True
        result.matches = sorted(matches, key=lambda obj: obj.score, reverse=True)
        if not suppress_debug and len(matches) > 1 and mode == "all":
            details = "\n".join(
                f"  {template_match.name} ({template_match.score * 100:.1f}% confidence)" for template_match in matches
            )
            msg = f"Found the following matches:\n{details}"
            LOGGER.debug(msg)
    elif not suppress_debug:
        LOGGER.debug(f"Could not find desired templates: {ref}")

    return result
