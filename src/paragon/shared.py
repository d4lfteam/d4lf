# ruff:file-ignore[useless-import-alias] - imported names are the preserved shared module attribute surface
"""Paragon overlay (tkinter)."""

# This module is the private shared-name facade for the split overlay mixins.

import base64 as base64
import configparser as configparser
import ctypes as ctypes
import io as io
import logging as logging
import re as re
import sys as sys
import threading as threading
import time as time
import tkinter as tk
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypedDict

from PIL import Image as Image
from PIL import ImageDraw as ImageDraw
from PIL import ImageFont as ImageFont
from PyQt6.QtCore import QSettings as QSettings

from src.automation import WindowSpec as WindowSpec
from src.automation import is_self_foreground as is_self_foreground
from src.automation import is_window_foreground as is_window_foreground
from src.desktop import call_on_ui_thread as call_on_ui_thread
from src.desktop import get_root as get_root
from src.desktop import is_alive as is_alive
from src.desktop import post_to_ui_thread as post_to_ui_thread
from src.item import Filter as Filter
from src.paragon.transform import GRID as GRID
from src.paragon.transform import NODES_LEN as NODES_LEN
from src.paragon.transform import nodes_to_grid as nodes_to_grid
from src.paragon.transform import parse_rotation as parse_rotation
from src.perception import game_window_roi as game_window_roi
from src.settings import get_settings as get_settings
from src.settings import get_ui_coordinates as get_ui_coordinates

if sys.platform == "win32":
    import win32con as win32con
    import win32gui as win32gui

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.paragon.overlay.controller import ParagonOverlay
    from src.profiles import ParagonBoardModel

LOGGER = logging.getLogger(__name__)


class OverlayContract(tk.Toplevel):
    """Shared Tk and dynamic-attribute contract for the overlay mixins."""

    _build_popup_bind_id: str | None
    _build_popup_escape_bind_id: str | None

    def __getattr__(self, name: str) -> Any:  # ruff:ignore[any-type] - dynamic Tk widget attributes
        raise AttributeError(name)


TRANSPARENT_KEY = "#ff00ff"
CARD_BG = "#151515"
TEXT = "#ffffff"
MUTED = "#cfcfcf"
ACCENT_GOLD = "#cfa15b"
ACCENT_GREEN = "#34C410"
ACCENT_BLUE = "#56B4E9"
SELECT_BG = "#1f1f1f"
FS_GRID_COLOR = "#3f3f3f"
PLAYER_CLASSES = ["barbarian", "druid", "necromancer", "rogue", "sorcerer", "spiritborn", "paladin", "warlock"]
BUILD_SOURCES = ["d4builds", "infinitybuilds", "maxroll", "mobalytics"]


class OverlaySettings(TypedDict, total=False):
    cell_size: int | None
    profile: str | None
    build_name: str | None
    build_idx: int | None
    board_idx: int | None
    grid_x: int | None
    grid_y: int | None
    is_collapsed: bool | None
    cell_size_collapsed: int | None
    grid_x_collapsed: int | None
    grid_y_collapsed: int | None
    grid_locked: bool | None
    gold_frames: bool | None


class BuildRow(TypedDict):
    name: str
    boards: list[ParagonBoardModel]
    profile: str


# =============================================================================
# GLOBALS
# =============================================================================

_CURRENT_OVERLAY: ParagonOverlay | None = None
_CLOSE_REQUESTED = threading.Event()
_OVERLAY_LOCK = threading.Lock()


# =============================================================================
# THEME & CONSTANTS
# =============================================================================

GOLD = ACCENT_GOLD
NODE_GREEN = ACCENT_GREEN
NODE_BLUE = ACCENT_BLUE

PANEL_W = 370
_TK_IMAGE_ATTRIBUTE = "image"

FS_PANEL_TITLE, FS_MODE_LABEL, FS_BUTTON, FS_BOARD_CARD = 13, 9, 12, 10
FS_BUILDS_MENU, FS_SETTINGS_ICON, FS_SETTINGS_LABEL, FS_ZOOM_BTN, FS_HINT = (12, 13, 10, 15, 10)
FS_CARD_FRAME, FS_GRID_FRAME = 1, 6


# =============================================================================
# UI FACTORY HELPERS
# =============================================================================


def _tk_btn(parent: tk.Misc, text: str = "", cmd: Callable[[], object] | None = None, **kw: object) -> tk.Button:
    """Creates a pre-styled Tkinter Button."""
    opts = {
        "bg": CARD_BG,
        "fg": TEXT,
        "activebackground": SELECT_BG,
        "activeforeground": GOLD,
        "bd": 0,
        "highlightthickness": 0,
    }
    opts.update(kw)
    button = tk.Button(parent, cnf=opts, text=text)
    if cmd is not None:
        button.configure(command=cmd)
    return button


def _tk_lbl(parent: tk.Misc, text: str = "", **kw: object) -> tk.Label:
    """Creates a pre-styled Tkinter Label."""
    opts = {"bg": CARD_BG, "fg": TEXT}
    opts.update(kw)
    return tk.Label(parent, cnf=opts, text=text)


# =============================================================================
# WINDOWS DPI HELPERS
# =============================================================================

_TK_BASELINE_SCALING = 96 / 72


def _dpi_scale_for_widget(w: tk.Misc) -> float:
    """Read the effective DPI scale for a widget, falling back safely."""
    with suppress(Exception):
        return float(ctypes.windll.user32.GetDpiForWindow(int(w.winfo_id()))) / 96.0
    with suppress(Exception):
        return float(w.tk.call("tk", "scaling")) * 72 / 96.0
    return 1.0


# =============================================================================
# SETTINGS & PROFILE LOADERS
# =============================================================================


@dataclass(slots=True)
class OverlayConfig:
    """Runtime configuration for overlay size, scaling, and persisted state."""

    cell_size: int = 24
    grid_x_default: int = PANEL_W + 24
    grid_y_default: int = 24

    cell_size_collapsed: int = 16
    grid_x_collapsed_default: int = 600
    grid_y_collapsed_default: int = 300

    ui_scale: float = 1.0
    panel_w: int = PANEL_W
    poll_ms: int = 250
    window_alpha: float = 0.86

    is_collapsed: bool = False
    grid_locked: bool = False
    gold_frames: bool = False


# =============================================================================
# PARAGON OVERLAY CLASS
# =============================================================================


__all__ = [name for name in globals() if not name.startswith("__")]
