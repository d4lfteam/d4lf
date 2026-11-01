"""Executable template-query behavior."""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, cast

import numpy as np

from src.perception.capture.core import Cam

from .config import SearchConfig
from .engine import search
from .models import ColorMatch, SearchResult, TemplateReferences

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .config import SearchMode

LOGGER = logging.getLogger(__name__)
type SearchArgValue = (
    TemplateReferences | np.ndarray | Sequence[int | float] | ColorMatch | str | int | float | bool | None
)


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
    use_parallel: bool = True

    @property
    def do_multi_process(self) -> bool:
        """Read the former option name while integrations migrate to ``use_parallel``."""
        return self.use_parallel

    @do_multi_process.setter
    def do_multi_process(self, value: bool) -> None:
        self.use_parallel = value

    def __call__(self, cls: type[Self]) -> type[Self]:
        cls._search_args = self
        return cls

    def as_dict(self) -> dict[str, SearchArgValue]:
        return self.__dict__

    def detect(self, img: np.ndarray | None = None) -> SearchResult:
        search_img = img if img is not None else self.inp_img
        if search_img is None:
            search_img = Cam().grab()
        return search(
            ref=self.ref,
            inp_img=search_img,
            config=SearchConfig(
                threshold=self.threshold,
                roi=self.roi,
                use_grayscale=self.use_grayscale,
                color_match=self.color_match,
                mode=cast("SearchMode", self.mode),
                timeout=self.timeout,
                suppress_debug=self.suppress_debug,
                use_parallel=self.use_parallel,
            ),
        )

    def is_visible(self, img: np.ndarray | None = None) -> bool:
        return self.detect(img).success
