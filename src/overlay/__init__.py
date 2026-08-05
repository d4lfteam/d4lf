"""Public overlay capability facade.

Tk rendering, settings storage, and platform details remain private to this package.
"""

from .base import Overlay
from .lifecycle import get_setting, is_open, open_overlay, request_close, update_stats
from .settings import load_settings, save_settings
from .statistics import SessionStats
from .tracking import InventoryExpTracker, set_busy_checker

__all__ = [
    "InventoryExpTracker",
    "Overlay",
    "SessionStats",
    "get_setting",
    "is_open",
    "load_settings",
    "open_overlay",
    "request_close",
    "save_settings",
    "set_busy_checker",
    "update_stats",
]
