import logging
import threading
import tkinter as tk
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.overlay.widget.widget import BossTimerOverlay

LOGGER = logging.getLogger(__name__)
_OVERLAY_INSTANCE: BossTimerOverlay | None = None
_OVERLAY_LOCK = threading.RLock()

TRANSPARENT_KEY = "#ff00ff"
CARD_BG = "#151515"
TEXT = "#ffffff"
MUTED = "#cfcfcf"
ACCENT_GOLD = "#cfa15b"
ACCENT_GREEN = "#34C410"
ACCENT_BLUE = "#56B4E9"


class OverlayContract(tk.Toplevel):
    """Shared Tk and dynamic-attribute contract for overlay mixins."""

    _gold_initialized: bool
    _exp_initialized: bool

    def __getattr__(self, name: str) -> Any:  # ruff:ignore[any-type] - dynamic Tk widget attributes
        raise AttributeError(name)


ACCENT = ACCENT_GOLD
LEGION_BLUE = ACCENT_BLUE
HELLTIDE_RED = "#ff4d4d"
WB_ORANGE = "#e67e22"
WARNING_ORANGE = "#ff9900"
ACTIVE_GREEN = ACCENT_GREEN
PROGRESS_YELLOW = "#ffff00"
