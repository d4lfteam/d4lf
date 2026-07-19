"""Public overlay capability facade.

Tk rendering, settings storage, and platform details remain private to this package.
"""

from .base import Overlay
from .lifecycle import get_setting, is_open, open_overlay, request_close, update_stats
from .settings import load_settings, save_settings
from .statistics import SessionStats
from .tracking import InventoryExpTracker, set_busy_checker

open_boss_timer_overlay = open_overlay
is_info_overlay_open = is_open
update_info_stats = update_stats
get_info_setting = get_setting
load_info_settings = load_settings
save_info_settings = save_settings

__all__ = [
    "InventoryExpTracker",
    "Overlay",
    "SessionStats",
    "get_info_setting",
    "is_info_overlay_open",
    "load_info_settings",
    "open_boss_timer_overlay",
    "request_close",
    "save_info_settings",
    "set_busy_checker",
    "update_info_stats",
    "update_stats",
]
