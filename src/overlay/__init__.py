"""Public overlay capability facade.

Tk rendering, settings storage, and platform details remain private to this package.
"""

from .base import Overlay
from .lifecycle import is_open, open_overlay, request_close
from .statistics import SessionStats
from .tracking import InventoryExpTracker, set_busy_checker

__all__ = [
    "InventoryExpTracker",
    "Overlay",
    "SessionStats",
    "is_open",
    "open_overlay",
    "request_close",
    "set_busy_checker",
]
