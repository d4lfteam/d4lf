"""Game-window detection and foreground-control interface."""

from .backend import WindowBackend, WindowSpecLike
from .core import (
    WindowSpec,
    detect_window,
    find_and_set_window_position,
    get_window_spec_id,
    is_self_foreground,
    is_window_foreground,
    move_window_to_foreground,
    start_detecting_window,
    stop_detecting_window,
)

__all__ = [
    "WindowBackend",
    "WindowSpec",
    "WindowSpecLike",
    "detect_window",
    "find_and_set_window_position",
    "get_window_spec_id",
    "is_self_foreground",
    "is_window_foreground",
    "move_window_to_foreground",
    "start_detecting_window",
    "stop_detecting_window",
]
