import logging
import tkinter as tk
from typing import NoReturn

LOGGER = logging.getLogger(__name__)

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

    def __getattr__(self, name: str) -> NoReturn:
        raise AttributeError(name)


ACCENT = ACCENT_GOLD
LEGION_BLUE = ACCENT_BLUE
HELLTIDE_RED = "#ff4d4d"
WB_ORANGE = "#e67e22"
WARNING_ORANGE = "#ff9900"
ACTIVE_GREEN = ACCENT_GREEN
PROGRESS_YELLOW = "#ffff00"
