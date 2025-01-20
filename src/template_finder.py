import logging
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np

from src import TP
from src.cam import Cam
from src.config.data import COLORS, Template
from src.config.ui import ResManager
from src.utils.image_operations import alpha_to_mask, color_filter, crop
from src.utils.misc import run_until_condition
from src.utils.roi_operations import get_center

LOGGER = logging.getLogger(__name__)

TEMPLATES_LOCK = threading.Lock()


@dataclass
class TemplateMatch:
    center: tuple[int, int] = None
    center_monitor: tuple[int, int] = None
    name: str = None
    region: list[int, int, int, int] = None
    region_monitor: list[int, int, int, int] = None
    score: float = -1.0

    def __eq__(self, other):
        if isinstance(other, TemplateMatch):
            return self.center == other.center and self.score == other.score
        return False

    def __hash__(self):
        return hash((self.center, self.score))


@dataclass
class SearchResult:
    matches: list[TemplateMatch] = None
    success: bool = False

    def __post_init__(self):
        if self.matches is None:
            self.matches = []


@dataclass
class SearchArgs:
    _search_args = None
    ref: str | np.ndarray | list[str]
    inp_img: np.ndarray | None = None
    threshold: float = 0.68
    roi: list[float] | str | None = None
    use_grayscale: bool = False
    color_match: list[float] | str | None = None
    mode: str = "first"
    timeout: int = 0
    suppress_debug: bool = True
    do_multi_process: bool = True

    def __call__(self, cls):
        cls._search_args = self
        return cls

    def as_dict(self):
        return self.__dict__

    def detect(self, img: np.ndarray = None) -> SearchResult:
        if img is not None:
            self.inp_img = img
        else:
            Cam().grab() if self.inp_img is None else self.inp_img
        return search(**self.as_dict())

    def is_visible(self, img: np.ndarray = None) -> bool:
        return self.detect(img).success

    def wait_until_visible(self, timeout: float = 30, suppress_debug: bool = False) -> SearchResult:
        if (
            not (result := run_until_condition(lambda: self.detect(), lambda match: match.success, timeout)[0]).success
            and not suppress_debug
        ):
            LOGGER.debug(f"{self.ref} not found after {timeout} seconds")
        return result

    def wait_until_hidden(self, timeout: float = 3, suppress_debug: bool = False) -> bool:
        if not (hidden := run_until_condition(lambda: self.detect().success, lambda res: not res, timeout)[1]) and not suppress_debug:
            LOGGER.debug(f"{self.ref} still found after {timeout} seconds")
        return hidden

    @staticmethod
    def wait_for_update(img: np.ndarray, roi: list[int] | None = None, timeout: float = 3, suppress_debug: bool = False) -> bool:
        roi = roi if roi is not None else [0, 0, img.shape[0] - 1, img.shape[1] - 1]
        if (
            not (
                change := run_until_condition(
                    lambda: crop(Cam().grab(), roi), lambda res: not np.array_equal(crop(img, roi), res), timeout
                )[1]
            )
            and not suppress_debug
        ):
            LOGGER.debug(f"ROI: '{roi}' unchanged after {timeout} seconds")
        return change


def _process_template_refs(ref: str | np.ndarray | list[str]) -> list[Template]:
    templates = []
    if not isinstance(ref, list):
        ref = [ref]
    for i in ref:
        # if the reference is a string, then it's a reference to a named template asset
        if isinstance(i, str):
            try:
                templates.append(ResManager().templates[i.lower()])
            except KeyError:
                LOGGER.warning(f"Template not defined: {i}")
        # if the reference is an image, append new Template class object
        elif isinstance(i, np.ndarray):
            templates.append(Template(img_bgr=i, img_gray=cv2.cvtColor(i, cv2.COLOR_BGR2GRAY), alpha_mask=alpha_to_mask(i)))
    return templates


def _get_cv_result(
    template: Template,
    inp_img: np.ndarray,
    roi: list[float] | None = None,
    color_match: list[float] | None = None,
    use_grayscale: bool = False,
) -> list[np.ndarray]:
    # crop image to roi
    if roi is None:
        # if no roi is provided roi = full inp_img
        roi = [0, 0, inp_img.shape[1], inp_img.shape[0]]
    roi = np.clip(np.array(roi), 0, None)
    rx, ry, rw, rh = roi
    img = inp_img[ry : ry + rh, rx : rx + rw]
    if img.shape[0] == 0 or img.shape[1] == 0:
        return None, template.img_bgr, roi

    # filter for desired color or make grayscale
    if color_match:
        _, template_img = color_filter(template.img_bgr, color_match)
        _, img = color_filter(img, color_match)
    elif use_grayscale:
        template_img = template.img_gray
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        template_img = template.img_bgr
    if not (img.shape[0] > template_img.shape[0] and img.shape[1] > template_img.shape[1]):
        # LOGGER.error(
        #     f"Image shape and template shape are incompatible: {template.name}. Image: {img.shape}, Template: {template_img.shape}, roi: {roi}"
        # )
        res = None
    else:
        res = cv2.matchTemplate(img, template_img, cv2.TM_CCOEFF_NORMED, mask=template.alpha_mask)
        np.nan_to_num(res, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    return res, template_img, roi


def search(
    ref: str | np.ndarray | list[str],
    inp_img: np.ndarray | None = None,
    threshold: float = 0.68,
    roi: list[float] | str | None = None,
    use_grayscale: bool = False,
    color_match: list[float] | str | None = None,
    mode: str = "first",
    timeout: int = 0,
    suppress_debug: bool = True,
    do_multi_process: bool = True,
) -> SearchResult:
    """
    Search for templates in an image
    :param ref: Either key of a already loaded template, list of such keys, or a image which is used as template
    :param inp_img: Image in which the template will be searched
    :param threshold: Threshold which determines if a template is found or not
    :param roi: Region of Interest of the inp_img to restrict search area. Format [left, top, width, height] or string corresponding to a key in Config().ui_roi
    :param use_grayscale: Use grayscale template matching for speed up
    :param color_match: Pass a color to be used by misc.color_filter to filter both image of interest and template image (format Config().colors["color"]) or string corresponding to a key in Config().colors
    :param mode: search "first" match or "all" matches
    :param timeout: wait for the specified number of seconds before stopping search
    :param do_multi_process: flag if multi process should be used in case there are multiple refs
    :return: SearchResult object containing success and matches
    """

    templates = _process_template_refs(ref)
    result = SearchResult()
    matches = []
    future_list = []
    if isinstance(roi, str):
        try:
            roi = getattr(ResManager().roi, roi)
        except KeyError as e:
            LOGGER.error(f"Invalid roi key: {roi}")
            LOGGER.error(e)
    if isinstance(color_match, str):
        try:
            color_match = getattr(COLORS, color_match)
        except KeyError as e:
            LOGGER.error(f"Invalid color_match key: {color_match}")
            LOGGER.error(e)

    def _process_cv_result(template: Template, img: np.ndarray) -> bool:
        new_match = False
        res, template_img, new_roi = _get_cv_result(template, img, roi, color_match, use_grayscale)

        # i = 0
        while True and not (matches and mode == "first") and res is not None:
            _, max_val, _, max_pos = cv2.minMaxLoc(res)

            if max_val >= threshold:
                new_match = True
                # Save rectangle corresponding to the matched region
                rec_x = int(max_pos[0] + new_roi[0])
                rec_y = int(max_pos[1] + new_roi[1])
                rec_w = int(template_img.shape[1])
                rec_h = int(template_img.shape[0])

                template_match = TemplateMatch()
                template_match.region = [rec_x, rec_y, rec_w, rec_h]
                template_match.region_monitor = [*Cam().window_to_monitor((rec_x, rec_y)), rec_w, rec_h]
                template_match.center = get_center(template_match.region)
                template_match.center_monitor = Cam().window_to_monitor(template_match.center)
                template_match.name = template.name
                template_match.score = max_val

                matches.append(template_match)
                if mode == "first":
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
            for template in templates:
                future = TP.submit(_process_cv_result, template, img)
                future_list.append(future)

                for i in future_list:
                    _ = i.result()
        else:
            for template in templates:
                res = _process_cv_result(template, img)
                if mode == "first" and res:
                    break

        time_remains = time.time() - start < timeout

    if matches:
        result.success = True
        result.matches = sorted(matches, key=lambda obj: obj.score, reverse=True)
        if not suppress_debug and len(matches) > 1 and mode == "all":
            LOGGER.debug(
                "Found the following matches:\n"
                + ", ".join([f"  {template_match.name} ({template_match.score * 100:.1f}% confidence)" for template_match in matches])
            )
    elif not suppress_debug:
        LOGGER.debug(f"Could not find desired templates: {ref}")

    return result
