import logging
from typing import TYPE_CHECKING

from src.desktop import OverlayContract, OverlaySlot

if TYPE_CHECKING:
    from datetime import datetime

    from src.overlay.widget.widget import BossTimerOverlay

LOGGER = logging.getLogger(__name__)

TRANSPARENT_KEY = "#ff00ff"
CARD_BG = "#151515"
TEXT = "#ffffff"
MUTED = "#cfcfcf"
ACCENT_GOLD = "#cfa15b"
ACCENT_GREEN = "#34C410"
ACCENT_BLUE = "#56B4E9"


BOSS_TIMER_SLOT: OverlaySlot[BossTimerOverlay] = OverlaySlot()


class BossTimerContract(OverlayContract):
    """Dynamic-attribute contract for the boss timer overlay mixins."""

    _gold_initialized: bool
    _exp_initialized: bool
    capture_gold_stats: bool
    capture_exp_stats: bool
    locked: bool
    synced_wb: tuple[datetime, str] | None


ACCENT = ACCENT_GOLD
LEGION_BLUE = ACCENT_BLUE
HELLTIDE_RED = "#ff4d4d"
WB_ORANGE = "#e67e22"
WARNING_ORANGE = "#ff9900"
ACTIVE_GREEN = ACCENT_GREEN
PROGRESS_YELLOW = "#ffff00"
