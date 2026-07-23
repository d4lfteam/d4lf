from src.overlay.widget.actions import _OverlayActions
from src.overlay.widget.controls import _OverlayControls
from src.overlay.widget.core import _OverlayCore
from src.overlay.widget.menu import _OverlayMenu
from src.overlay.widget.timers import _OverlayTimers
from src.overlay.widget.ui import _OverlayUI


class BossTimerOverlay(_OverlayCore, _OverlayUI, _OverlayControls, _OverlayMenu, _OverlayActions, _OverlayTimers):
    """The original Windows Tk boss-timer implementation, split by cohesive behavior."""
