from typing import TYPE_CHECKING, Protocol, cast

from . import listener as _listener
from .parser.item import parse_item_text

if TYPE_CHECKING:
    import numpy as np

    from .matching.models import SearchResult, TemplateReferences

from .geometry import (
    BulletMatchDiagnostics,
    DiagnosticLocatorResult,
    LocatedMarker,
    LocatorDiagnostics,
    LocatorResult,
    TemplateMatchTrace,
    locate_affix_markers,
    locate_affix_markers_with_diagnostics,
)
from .matching import SearchResult, TemplateMatch
from .polling import run_until_condition
from .screenshot import screenshot
from .text import (
    clean_str,
    closest_match,
    closest_to,
    correct_name,
    find_number,
    keep_letters_and_spaces,
    remove_text_after_first_keyword,
)
from .tooltip import DescrDetection, find_descr, find_descr_with_diagnostics, get_separator_match_in_crop

Publisher = _listener.Publisher
filter_data = _listener.filter_data
find_item_start = _listener.find_item_start
fix_data = _listener.fix_data


def read_latest_item():
    return parse_item_text(list(_listener.LAST_ITEM))


def latest_item_lines() -> list[str]:
    return list(_listener.LAST_ITEM)


def is_connected() -> bool:
    return _listener.CONNECTED


def start_connection() -> None:
    _listener.start_connection()


class TemplateQuery(Protocol):
    ref: TemplateReferences
    mode: str

    def detect(self, img: np.ndarray | None = None) -> SearchResult: ...

    def is_visible(self, img: np.ndarray | None = None) -> bool: ...


def capture(force_new: bool = False):
    from .capture.core import Cam  # ruff:ignore[import-outside-top-level]

    return Cam().grab(force_new=force_new)


def game_window_ready() -> bool:
    from .capture.core import Cam  # ruff:ignore[import-outside-top-level]

    return Cam().is_offset_set()


def game_window_roi() -> dict[str, int]:
    from .capture.core import Cam  # ruff:ignore[import-outside-top-level]

    return cast("dict[str, int]", dict(Cam().window_roi))


def monitor_to_window(coordinate):
    from .capture.core import Cam  # ruff:ignore[import-outside-top-level]

    return Cam().monitor_to_window(coordinate)


def window_to_monitor(coordinate):
    from .capture.core import Cam  # ruff:ignore[import-outside-top-level]

    return Cam().window_to_monitor(coordinate)


def abs_window_to_monitor(coordinate):
    from .capture.core import Cam  # ruff:ignore[import-outside-top-level]

    return Cam().abs_window_to_monitor(coordinate)


def update_window_position(offset_x: int, offset_y: int, width: int, height: int) -> None:
    from .capture.core import Cam  # ruff:ignore[import-outside-top-level]

    Cam().update_window_pos(offset_x, offset_y, width, height)


def reset_window_position() -> None:
    from .capture.core import Cam  # ruff:ignore[import-outside-top-level]

    Cam().reset_window_position()


def create_template_query(**kwargs) -> TemplateQuery:
    from .matching.models import SearchArgs  # ruff:ignore[import-outside-top-level]

    return SearchArgs(**kwargs)


def search_templates(*args, **kwargs):
    from .matching.engine import search  # ruff:ignore[import-outside-top-level]

    return search(*args, **kwargs)


def crop_image(image, roi):
    from .image import crop  # ruff:ignore[import-outside-top-level]

    return crop(image, roi)


def alpha_mask(image):
    from .image import alpha_to_mask  # ruff:ignore[import-outside-top-level]

    return alpha_to_mask(image)


def compare_image_histograms(image_a, image_b):
    from .image import compare_histograms  # ruff:ignore[import-outside-top-level]

    return compare_histograms(image_a, image_b)


def center_of_roi(roi):
    from .roi import get_center  # ruff:ignore[import-outside-top-level]

    return get_center(roi)


def grid_rois(roi, rows: int, columns: int):
    from .roi import to_grid  # ruff:ignore[import-outside-top-level]

    return to_grid(roi, rows, columns)


__all__ = [
    "BulletMatchDiagnostics",
    "DescrDetection",
    "DiagnosticLocatorResult",
    "LocatedMarker",
    "LocatorDiagnostics",
    "LocatorResult",
    "Publisher",
    "SearchResult",
    "TemplateMatch",
    "TemplateMatchTrace",
    "TemplateQuery",
    "abs_window_to_monitor",
    "alpha_mask",
    "capture",
    "center_of_roi",
    "clean_str",
    "closest_match",
    "closest_to",
    "compare_image_histograms",
    "correct_name",
    "create_template_query",
    "crop_image",
    "filter_data",
    "find_descr",
    "find_descr_with_diagnostics",
    "find_item_start",
    "find_number",
    "fix_data",
    "game_window_ready",
    "game_window_roi",
    "get_separator_match_in_crop",
    "grid_rois",
    "is_connected",
    "keep_letters_and_spaces",
    "latest_item_lines",
    "locate_affix_markers",
    "locate_affix_markers_with_diagnostics",
    "monitor_to_window",
    "parse_item_text",
    "read_latest_item",
    "remove_text_after_first_keyword",
    "reset_window_position",
    "run_until_condition",
    "screenshot",
    "search_templates",
    "start_connection",
    "update_window_position",
    "window_to_monitor",
]
