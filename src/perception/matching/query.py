"""Executable template-query behavior."""

import logging
import operator
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from src.perception.capture.core import Cam
from src.perception.image import crop
from src.perception.polling import run_until_condition

from .engine import search
from .models import ColorMatch, Rectangle, SearchResult, TemplateReferences

if TYPE_CHECKING:
    from collections.abc import Sequence

LOGGER = logging.getLogger(__name__)


@dataclass
class SearchArgs:
    """Arguments and convenience operations for one template search."""

    _search_args = None
    ref: TemplateReferences
    inp_img: np.ndarray | None = None
    threshold: float = 0.68
    roi: Sequence[int | float] | str | None = None
    use_grayscale: bool = False
    color_match: ColorMatch = None
    mode: str = "first"
    timeout: int = 0
    suppress_debug: bool = True
    do_multi_process: bool = True

    def __call__(self, cls):
        cls._search_args = self
        return cls

    def as_dict(self):
        return self.__dict__

    def detect(self, img: np.ndarray | None = None) -> SearchResult:
        if img is not None:
            self.inp_img = img
        elif self.inp_img is None:
            Cam().grab()
        return search(**self.as_dict())

    def is_visible(self, img: np.ndarray | None = None) -> bool:
        return self.detect(img).success

    def wait_until_visible(self, timeout: float = 30, suppress_debug: bool = False) -> SearchResult:
        raw_result, _ = run_until_condition(lambda: self.detect(), lambda match: match.success, timeout)
        result = raw_result if isinstance(raw_result, SearchResult) else SearchResult()
        if not result.success and not suppress_debug:
            LOGGER.debug(f"{self.ref} not found after {timeout} seconds")
        return result

    def wait_until_hidden(self, timeout: float = 3, suppress_debug: bool = False) -> bool:
        if (
            not (hidden := run_until_condition(lambda: self.detect().success, operator.not_, timeout)[1])
            and not suppress_debug
        ):
            LOGGER.debug(f"{self.ref} still found after {timeout} seconds")
        return hidden

    @staticmethod
    def wait_for_update(
        img: np.ndarray, roi: Rectangle | None = None, timeout: float = 3, suppress_debug: bool = False
    ) -> bool:
        resolved_roi = roi if roi is not None else (0, 0, img.shape[0] - 1, img.shape[1] - 1)
        if (
            not (
                change := run_until_condition(
                    lambda: crop(Cam().grab(), resolved_roi),
                    lambda res: not np.array_equal(crop(img, resolved_roi), res),
                    timeout,
                )[1]
            )
            and not suppress_debug
        ):
            LOGGER.debug(f"ROI: '{resolved_roi}' unchanged after {timeout} seconds")
        return change
