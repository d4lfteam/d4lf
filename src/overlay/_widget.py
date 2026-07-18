from ._widget_actions import _OverlayActions
from ._widget_controls import _OverlayControls
from ._widget_core import _OverlayCore
from ._widget_menu import _OverlayMenu
from ._widget_timers import _OverlayTimers
from ._widget_ui import _OverlayUI


class BossTimerOverlay(_OverlayCore, _OverlayUI, _OverlayControls, _OverlayMenu, _OverlayActions, _OverlayTimers):
    """The original Windows Tk boss-timer implementation, split by cohesive behavior."""
