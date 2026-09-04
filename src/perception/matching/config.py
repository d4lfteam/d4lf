"""Validated configuration for one template search."""

from dataclasses import dataclass
from math import isfinite
from typing import TYPE_CHECKING, Literal

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from .models import ColorMatch, TemplateMatch

SearchMode = Literal["first", "all"]


@dataclass(frozen=True, slots=True)
class SearchConfig:
    """Options that control matching, independent of templates and input images."""

    threshold: float = 0.7
    roi: Sequence[int | float] | str | None = None
    use_grayscale: bool = False
    color_match: ColorMatch = None
    mode: SearchMode = "first"
    timeout: float = 0
    suppress_debug: bool = True
    use_parallel: bool = True
    take_debug_screenshot: bool = False
    stop_condition: Callable[[list[TemplateMatch]], bool] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.threshold, (int, float, np.number)) or not isfinite(float(self.threshold)):
            message = "threshold must be a finite number"
            raise ValueError(message)
        if self.mode not in ("first", "all"):
            message = f"Invalid search mode: {self.mode}"
            raise ValueError(message)
        if not isinstance(self.timeout, (int, float, np.number)) or not isfinite(float(self.timeout)):
            message = "timeout must be a finite number"
            raise ValueError(message)
        if self.timeout < 0:
            message = "timeout must not be negative"
            raise ValueError(message)
        if self.roi is not None and not isinstance(self.roi, str):
            try:
                values = tuple(self.roi)
            except TypeError as error:
                message = "roi must contain four values"
                raise ValueError(message) from error
            if len(values) != 4:
                message = "roi must contain four values"
                raise ValueError(message)
            if any(not isinstance(value, (int, float, np.number)) for value in values):
                message = "roi must contain numeric values"
                raise ValueError(message)
            if not all(isfinite(float(value)) for value in values):
                message = "roi must contain finite values"
                raise ValueError(message)
            if values[0] < 0 or values[1] < 0 or values[2] <= 0 or values[3] <= 0:
                message = "roi must have a non-negative origin and positive dimensions"
                raise ValueError(message)
        if not isinstance(self.use_grayscale, bool):
            message = "use_grayscale must be a boolean"
            raise ValueError(message)
        if not isinstance(self.suppress_debug, bool):
            message = "suppress_debug must be a boolean"
            raise ValueError(message)
        if not isinstance(self.use_parallel, bool):
            message = "use_parallel must be a boolean"
            raise ValueError(message)
        if not isinstance(self.take_debug_screenshot, bool):
            message = "take_debug_screenshot must be a boolean"
            raise ValueError(message)
        if self.stop_condition is not None and not callable(self.stop_condition):
            message = "stop_condition must be callable"
            raise ValueError(message)
