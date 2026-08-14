from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy as np

    from src.item import Item

from . import listener as _listener
from .capture.core import Cam
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
from .image import alpha_to_mask, compare_histograms, crop
from .matching import SearchArgs, SearchResult, TemplateMatch, search
from .parser.item import parse_item_text
from .polling import run_until_condition
from .roi import get_center, to_grid
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


def read_latest_item() -> Item | None:
    return parse_item_text(list(_listener.LAST_ITEM))


def latest_item_lines() -> list[str]:
    return list(_listener.LAST_ITEM)


def is_connected() -> bool:
    return _listener.CONNECTED


def start_connection() -> None:
    _listener.start_connection()


def capture(force_new: bool = False) -> np.ndarray:
    return Cam().grab(force_new=force_new)


def game_window_ready() -> bool:
    return Cam().is_offset_set()


def game_window_roi() -> dict[str, int]:
    roi = Cam().window_roi
    return {"top": roi["top"], "left": roi["left"], "width": roi["width"], "height": roi["height"]}


def monitor_to_window(coordinate: Sequence[int | float] | np.ndarray) -> np.ndarray:
    return Cam().monitor_to_window(coordinate)


def window_to_monitor(coordinate: Sequence[int | float] | np.ndarray) -> np.ndarray:
    return Cam().window_to_monitor(coordinate)


def abs_window_to_monitor(coordinate: Sequence[int | float] | np.ndarray) -> np.ndarray:
    return Cam().abs_window_to_monitor(coordinate)


def update_window_position(offset_x: int, offset_y: int, width: int, height: int) -> None:
    Cam().update_window_pos(offset_x, offset_y, width, height)


def reset_window_position() -> None:
    Cam().reset_window_position()


__all__ = [
    "BulletMatchDiagnostics",
    "DescrDetection",
    "DiagnosticLocatorResult",
    "LocatedMarker",
    "LocatorDiagnostics",
    "LocatorResult",
    "Publisher",
    "SearchArgs",
    "SearchResult",
    "TemplateMatch",
    "TemplateMatchTrace",
    "abs_window_to_monitor",
    "alpha_to_mask",
    "capture",
    "clean_str",
    "closest_match",
    "closest_to",
    "compare_histograms",
    "correct_name",
    "crop",
    "filter_data",
    "find_descr",
    "find_descr_with_diagnostics",
    "find_item_start",
    "find_number",
    "fix_data",
    "game_window_ready",
    "game_window_roi",
    "get_center",
    "get_separator_match_in_crop",
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
    "search",
    "start_connection",
    "to_grid",
    "update_window_position",
    "window_to_monitor",
]
