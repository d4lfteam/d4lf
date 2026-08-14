import datetime
import time
import tkinter as tk
from contextlib import suppress
from typing import TYPE_CHECKING, Protocol, cast, override

from src.automation import WindowSpec
from src.overlay import state as _state
from src.overlay.settings import InfoSettingValue
from src.overlay.settings import load_settings as load_info_settings
from src.overlay.settings import save_settings as save_info_settings
from src.overlay.settings import setting_bool as _setting_bool
from src.overlay.settings import setting_datetime as _setting_datetime
from src.overlay.settings import setting_int as _setting_int
from src.overlay.settings import setting_str as _setting_str
from src.overlay.statistics import SessionStats
from src.overlay.widget.shared import TRANSPARENT_KEY, OverlayContract
from src.perception import game_window_roi
from src.settings import get_settings

if TYPE_CHECKING:
    from src.overlay.widget.widget import BossTimerOverlay


class _OverlayClosed(Protocol):
    def __call__(self, overlay: BossTimerOverlay | None) -> None: ...


class _OverlayCore(OverlayContract):
    def __init__(self, parent: tk.Misc, on_closed: _OverlayClosed | None = None) -> None:
        super().__init__(parent)
        self._on_closed = on_closed
        self._after_ids: list[str] = []
        self._closing: bool = False
        self._gold_initialized: bool = False
        self._exp_initialized: bool = False
        self._is_dragging: bool = False
        self._menu_vars: list[tk.Variable] = []  # Initialize here to store tk.Variable instances
        self._settings_popup: tk.Toplevel | None = None
        self._last_focus_time: float = time.time()
        self._last_menu_pos: tuple[int, int] = (100, 100)
        self._open_submenus: dict[str, tk.Toplevel] = {}  # To keep track of open submenus
        self.settings: dict[str, InfoSettingValue]
        self.x: int
        self.y: int
        self.font_size: int
        self.next_boss_name: str
        self.orientation: str
        self.locked: bool
        self.font_family: str
        self.capture_gold_stats: bool
        self.capture_exp_stats: bool
        self.show_wb: bool
        self.show_legion: bool
        self.show_ht: bool
        self.show_gold: bool
        self.show_gph: bool
        self.show_total_gold: bool
        self.show_exp: bool
        self.show_eph: bool
        self.show_total_exp: bool
        self.show_t2l: bool
        self.show_next_scan: bool
        self.wb_reference: datetime.datetime
        self.synced_wb: tuple[datetime.datetime, str] | None
        self.synced_legion: datetime.datetime | None
        self.synced_helltide: datetime.datetime | None
        self.labels_to_resize: list[tk.Label] = []

        self.title("D4LF Boss Timer")
        self.attributes("-topmost", 1)
        self.overrideredirect(boolean=True)
        self.wm_attributes("-transparentcolor", TRANSPARENT_KEY)
        self.configure(bg=TRANSPARENT_KEY)

        self._win_spec = WindowSpec(get_settings().advanced_options.process_name)

        self.settings = load_info_settings()
        self._apply_loaded_settings()

        self._flash_toggle = False
        self._setup_ui()
        self._bind_events()
        self._update_timers()  # Initial update for timers

        self._session_stats = SessionStats()
        self._session_stats.subscribe()
        self._auto_sync()

    @override
    def destroy(self) -> None:
        """Perform cleanup and unsubscribe from stats on destruction."""
        if self._closing:
            return
        self._closing = True

        # Cancel all pending after calls to avoid Tcl_AsyncDelete errors
        for after_id in self._after_ids:
            with suppress(Exception):
                self.after_cancel(after_id)
        self._after_ids.clear()

        self._destroy_settings_popup()
        self._close_all_submenus()

        self._session_stats.unsubscribe()
        self._menu_vars.clear()

        # The root is the shared UI thread's root, not ours to tear down —
        # only destroy this Toplevel.
        super().destroy()

        if self._on_closed is not None:
            self._on_closed(cast("BossTimerOverlay", self))
        else:
            _state.clear_overlay(cast("BossTimerOverlay", self))

    def _apply_loaded_settings(self) -> None:
        # Transition to relative coordinates: Add the current game window offset to the saved position.
        roi = game_window_roi()
        offset_x = roi.get("left", 0) if roi else 0
        offset_y = roi.get("top", 0) if roi else 0
        self.x = _setting_int(self.settings, "x", 100) + offset_x
        self.y = _setting_int(self.settings, "y", 100) + offset_y
        self.font_size = _setting_int(self.settings, "font_size", 14)
        self.next_boss_name = _setting_str(self.settings, "next_boss_name", "Unknown")
        self.orientation = _setting_str(self.settings, "orientation", "horizontal")
        self.locked = _setting_bool(self.settings, "locked", default=False)
        self.font_family = _setting_str(self.settings, "font_family", "Consolas")
        self.capture_gold_stats = _setting_bool(self.settings, "capture_gold_stats", default=False)
        self.capture_exp_stats = _setting_bool(self.settings, "capture_exp_stats", default=False)
        self.show_wb = _setting_bool(self.settings, "show_wb", default=True)
        self.show_legion = _setting_bool(self.settings, "show_legion", default=True)
        self.show_ht = _setting_bool(self.settings, "show_ht", default=True)
        self.show_gold = _setting_bool(self.settings, "show_gold", default=True)
        self.show_gph = _setting_bool(self.settings, "show_gph", default=True)
        self.show_total_gold = _setting_bool(self.settings, "show_total_gold", default=True)
        self.show_exp = _setting_bool(self.settings, "show_exp", default=True)
        self.show_eph = _setting_bool(self.settings, "show_eph", default=True)
        self.show_total_exp = _setting_bool(self.settings, "show_total_exp", default=True)
        self.show_t2l = _setting_bool(self.settings, "show_t2l", default=True)
        self.show_next_scan = _setting_bool(self.settings, "show_next_scan", default=True)
        self.wb_reference = _setting_datetime(
            self.settings, "wb_reference", datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
        )

        # In-memory synced data
        self.synced_wb = None
        self.synced_legion = None
        self.synced_helltide = None

        stats = SessionStats()
        self._gold_initialized = self.capture_gold_stats and stats.last_gold is not None
        self._exp_initialized = self.capture_exp_stats and stats.last_exp is not None

    def _save_settings(self) -> None:
        roi = game_window_roi()
        offset_x = roi.get("left", 0) if roi else 0
        offset_y = roi.get("top", 0) if roi else 0
        updates: dict[str, InfoSettingValue] = {
            "x": self.winfo_x() - offset_x,
            "y": self.winfo_y() - offset_y,
            "font_size": self.font_size,
            "wb_reference": self.wb_reference,
            "next_boss_name": self.next_boss_name,
            "orientation": self.orientation,
            "font_family": self.font_family,
            "locked": self.locked,
            "capture_gold_stats": self.capture_gold_stats,
            "capture_exp_stats": self.capture_exp_stats,
        }
        # Sync show_ attributes
        for k in self.settings:
            if k.startswith("show_"):
                updates[k] = getattr(self, k)

        if updates:  # Only save if there are actual updates
            save_info_settings(updates)

        # Update local cache instead of reloading to avoid race conditions with OS disk/registry writes
        self.settings.update(updates)

    def _is_descendant(self, child: tk.Misc, parent: tk.Misc) -> bool:
        """Return True if child is parent or a descendant of parent."""
        w: tk.Misc | None = child
        while w:
            if w is parent:
                return True
            try:
                w = getattr(w, "master", None)
                if not isinstance(w, tk.Misc):
                    break
            except AttributeError, RuntimeError, tk.TclError:
                break
        return False
