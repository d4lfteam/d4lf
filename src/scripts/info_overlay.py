from __future__ import annotations

import datetime
import logging
import re
import threading
import time
import tkinter as tk
from contextlib import suppress
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import httpx
from PyQt6.QtCore import QSettings

from src.cam import Cam
from src.config.helper import singleton
from src.config.loader import IniConfigLoader
from src.scripts.common import get_filter_colors
from src.tts import Publisher
from src.utils.custom_mouse import mouse

LOGGER = logging.getLogger(__name__)

_OVERLAY_INSTANCE: BossTimerOverlay | None = None
_OVERLAY_LOCK = threading.RLock()


def _default_busy_checker() -> bool:
    return False


_BUSY_CHECKER: Callable[[], bool] = _default_busy_checker


def set_busy_checker(checker: Callable[[], bool]):
    """Hook for the script handler to provide a busy state check."""
    global _BUSY_CHECKER
    _BUSY_CHECKER = checker


def load_info_settings() -> dict[str, Any]:
    """Load info overlay and experience tracking settings from QSettings."""
    settings_q = QSettings("d4lf", "InfoOverlay")

    def get_value(key: str, default: Any, type_hint: type) -> Any:
        return settings_q.value(key, default, type=type_hint)

    def parse_int_from_qsettings(k: str, default: int) -> int:
        try:
            return int(settings_q.value(k, str(default), type=str))
        except ValueError:
            return default

    def parse_tuple_from_qsettings(k: str) -> tuple[int, ...] | None:
        v = settings_q.value(k, None, type=str)
        if not v or v.lower() == "none":
            return None
        try:
            return tuple(int(x.strip()) for x in v.strip("()").replace(",", " ").split())
        except Exception:
            return None

    # Boss Timer UI Settings
    loaded_settings = {
        "x": get_value("x", 100, int),
        "y": get_value("y", 100, int),
        "font_size": get_value("font_size", 14, int),
        "wb_reference": get_value("wb_reference", "2024-01-01 00:00:00", str),
        "next_boss_name": get_value("next_boss_name", "Unknown", str),
        "orientation": get_value("orientation", "horizontal", str),
        "show_wb": get_value("show_wb", True, bool),
        "show_legion": get_value("show_legion", True, bool),
        "show_ht": get_value("show_ht", True, bool),
        "show_gold": get_value("show_gold", True, bool),
        "show_gph": get_value("show_gph", True, bool),
        "show_total_gold": get_value("show_total_gold", True, bool),
        "show_exp": get_value("show_exp", True, bool),
        "show_eph": get_value("show_eph", True, bool),
        "show_total_exp": get_value("show_total_exp", True, bool),
        "show_t2l": get_value("show_t2l", True, bool),
        "show_next_scan": get_value("show_next_scan", True, bool),
        "font_family": get_value("font_family", "Consolas", str),
        "capture_gold_stats": get_value("capture_gold_stats", False, bool),
        "capture_exp_stats": get_value("capture_exp_stats", False, bool),
        "locked": get_value("locked", False, bool),
        # Experience/Tracking Settings (Moved from GeneralModel)
        "check_exp_on_inventory_open": get_value("check_exp_on_inventory_open", True, bool),
        "exp_age_before_refresh": get_value("exp_age_before_refresh", 5, int),
        "exp_bar_pos": parse_tuple_from_qsettings("exp_bar_pos"),
    }
    # Convert wb_reference string to datetime object
    wb_ref = loaded_settings["wb_reference"]
    if isinstance(wb_ref, str):
        try:
            loaded_settings["wb_reference"] = datetime.datetime.strptime(wb_ref, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=datetime.UTC
            )
        except ValueError, TypeError:
            loaded_settings["wb_reference"] = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
    elif not isinstance(wb_ref, datetime.datetime):
        loaded_settings["wb_reference"] = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)

    return loaded_settings


def save_info_settings(values: dict[str, Any]) -> None:
    """Persist settings to the QSettings for InfoOverlay."""
    settings_q = QSettings("d4lf", "InfoOverlay")

    for k, v in values.items():
        if k == "wb_reference":
            if isinstance(v, datetime.datetime):
                settings_q.setValue(k, v.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                settings_q.setValue(k, v)
        elif k == "exp_bar_pos":
            settings_q.setValue(k, str(v) if v is not None else "None")
        else:
            settings_q.setValue(k, v)


def get_info_setting(key: str, default: Any = None) -> Any:
    """Quick access to a specific info overlay setting."""
    return load_info_settings().get(key, default)


def update_info_stats(**kwargs):
    with _OVERLAY_LOCK:
        if _OVERLAY_INSTANCE is not None:
            _OVERLAY_INSTANCE.update_stats(**kwargs)


def _hover_experience_balance(info_config: dict[str, Any]):
    pos = info_config.get("exp_bar_pos")
    if pos:
        if isinstance(pos, str):
            with suppress(Exception):
                pos = tuple(int(x.strip()) for x in pos.strip("()").replace(",", " ").split())
        if pos and len(pos) == 4:
            p1 = (pos[0], pos[1])
            p2 = (pos[2], pos[3])
            mouse.move(*Cam().window_to_monitor(p1))
            time.sleep(0.1)
            mouse.move(*Cam().window_to_monitor(p2))
            return

    # Default fallback: bottom center
    res = Cam().window_roi
    if res:
        target = (res["width"] // 2, res["height"] - 10)
        mouse.move(*Cam().window_to_monitor(target))


def request_close():
    with _OVERLAY_LOCK:
        if _OVERLAY_INSTANCE is not None:
            _OVERLAY_INSTANCE.after(0, lambda: _OVERLAY_INSTANCE.master.destroy())


@singleton
class SessionStats:
    def __init__(self):
        self.start_time = None
        self.total_gold = 0
        self.total_exp = 0
        self.pending_gold = None
        self.gold_verify_count = 0
        self.last_gold = None
        self.last_exp = None
        self.max_exp = None

        self._is_subscribed = False

    def subscribe(self):
        if not self._is_subscribed:
            Publisher().subscribe_info(self.on_info_stat)
            self._is_subscribed = True
            LOGGER.debug("SessionStats subscribed to TTS info.")

    def unsubscribe(self):
        if self._is_subscribed:
            Publisher().unsubscribe_info(self.on_info_stat)
            self._is_subscribed = False
            LOGGER.debug("SessionStats unsubscribed from TTS info.")

    def reset_gold(self):
        self.total_gold = 0
        self.pending_gold = None
        self.gold_verify_count = 0
        if hasattr(self, "last_gold"):
            self.last_gold = None
        LOGGER.info("Gold session stats reset")

    def reset_exp(self):
        self.total_exp = 0
        self.last_exp = None
        LOGGER.info("Experience session stats reset")

    def on_info_stat(self, raw_line: str):
        """Callback for parsed info statistics."""
        # Handle Gold statistics from raw TTS string (e.g., '2,225,130,802 Gold')
        info_config = load_info_settings()
        if not info_config["capture_gold_stats"] and not info_config["capture_exp_stats"]:
            return
        if (
            "gold" in raw_line.lower()
            and not any(
                x in raw_line.lower()
                for x in ["sell value", "repair", "cost", "price", "buy", "fee", "spent", "purchase"]
            )
            and (match := re.search(r"([0-9,.]+)\s+Gold", raw_line, re.IGNORECASE))
        ):
            if not info_config["capture_gold_stats"]:
                return
            raw_val = re.sub(r"\D", "", match.group(1))
            if not raw_val:
                return
            val = int(raw_val)
            LOGGER.debug(f"TTS Stat detected: gold_balance={val}")

            if self.last_gold is None:
                self.last_gold, self.start_time = val, self.start_time or time.time()
                update_info_stats(gph=0, total_gained=0)
                return
            if val == self.last_gold:
                self.pending_gold, self.gold_verify_count = None, 0
                return
            if self.pending_gold is not None and val >= self.pending_gold:
                self.gold_verify_count += 1
                self.pending_gold = val
            else:
                self.pending_gold, self.gold_verify_count = val, 1

            if self.gold_verify_count >= 3:
                if (self.last_gold > 0 and val > self.last_gold * 10 and val > 10_000_000) or (
                    val < self.last_gold * 0.01 and self.last_gold > 10_000_000
                ):
                    self.last_gold = val
                else:
                    delta = val - self.last_gold
                    if delta > 0:
                        self.total_gold += delta
                    elapsed = (time.time() - self.start_time) / 3600.0
                    gph = int(self.total_gold / elapsed) if elapsed > (1 / 60.0) else 0
                    update_info_stats(gph=gph, total_gained=self.total_gold)
                    self.last_gold = val
                self.pending_gold, self.gold_verify_count = None, 0

        # Handle Experience statistics (e.g., 'Level 209 Experience: 55,843,725 / 74,304,757')
        elif "experience" in raw_line.lower() and (
            match := re.search(r"Experience:\s+([0-9,.]+)\s+/\s+([0-9,.]+)", raw_line, re.IGNORECASE)
        ):
            if not info_config["capture_exp_stats"]:
                return
            raw_val = re.sub(r"\D", "", match.group(1))
            raw_mx = re.sub(r"\D", "", match.group(2))
            if not (raw_val and raw_mx):
                return
            val, mx_val = int(raw_val), int(raw_mx)
            LOGGER.debug(f"TTS Stat detected: experience_gain={val}")

            if self.last_exp is None:
                self.last_exp, self.max_exp, self.start_time = val, mx_val, self.start_time or time.time()
                update_info_stats(eph=0, total_exp=0, t2l="-")
                return
            delta = val - self.last_exp
            if delta > 0:
                self.total_exp += delta
            self.last_exp, self.max_exp = val, mx_val or self.max_exp
            elapsed = (time.time() - self.start_time) / 3600.0
            eph = int(self.total_exp / elapsed) if elapsed > (1 / 60.0) else 0
            t2l = "-"
            if eph > 0 and self.max_exp:
                hours = (self.max_exp - val) / eph
                t2l = f"{int(hours * 60)}m" if hours < 1 else f"{int(hours)}h {int((hours % 1) * 60)}m"
            update_info_stats(eph=eph, total_exp=self.total_exp, t2l=t2l)


@singleton
class InventoryExpTracker:
    def __init__(self):
        self.last_hover_time = 0
        self.hover_active = False

    def on_inventory_open(self):
        if self.hover_active or _BUSY_CHECKER():
            return

        with _OVERLAY_LOCK:
            if _OVERLAY_INSTANCE is None:
                return

        info_config = load_info_settings()
        if not info_config.get("capture_exp_stats", False):
            return
        exp_age = info_config.get("exp_age_before_refresh", 5)
        if exp_age == -1:
            return
        if not info_config.get("check_exp_on_inventory_open", True):
            return
        if IniConfigLoader().advanced_options.vision_mode_only:
            return

        now = time.time()
        is_init = SessionStats().last_exp is not None
        if (now - self.last_hover_time) < (exp_age * 60 if is_init else 2.0):
            return

        def _task():
            try:
                self.hover_active = True
                time.sleep(0.5)
                _hover_experience_balance(info_config)
                mouse.move(*Cam().abs_window_to_monitor((0, 0)))
            finally:
                self.hover_active = False

        self.last_hover_time = now
        threading.Thread(target=_task, daemon=True).start()


TRANSPARENT_KEY = "#ff00ff"
CARD_BG = "#151515"
TEXT = "#ffffff"
MUTED = "#cfcfcf"
ACCENT = "#cfa15b"
LEGION_BLUE = "#56B4E9"
HELLTIDE_RED = "#ff4d4d"
WB_ORANGE = "#e67e22"
WARNING_ORANGE = "#ff9900"
ACTIVE_GREEN = "#34C410"
PROGRESS_YELLOW = "#ffff00"


class BossTimerOverlay(tk.Toplevel):
    FONT_CHOICES = [
        "Arial",
        "Consolas",
        "Constantia",
        "Copperplate Gothic Bold",
        "Courier New",
        "Garamond",
        "Georgia",
        "Impact",
        "Palatino Linotype",
        "Segoe UI",
        "Tahoma",
        "Times New Roman",
        "Trebuchet MS",
        "Verdana",
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("D4LF Boss Timer")
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.wm_attributes("-transparentcolor", TRANSPARENT_KEY)
        self.configure(bg=TRANSPARENT_KEY)

        self._gold_initialized = False
        self._exp_initialized = False
        self._menu_vars = []  # Initialize here to store tk.Variable instances
        self._settings_popup = None
        self._last_menu_pos = (100, 100)

        self.settings = load_info_settings()
        self._apply_loaded_settings()
        self._flash_toggle = False
        self._setup_ui()
        self._bind_events()
        self._open_submenus: dict[str, tk.Toplevel] = {}  # To keep track of open submenus
        self._update_timers()  # Initial update for timers

        self._session_stats = SessionStats()
        self._session_stats.subscribe()
        self._auto_sync()

    def destroy(self):
        """Perform cleanup and unsubscribe from stats on destruction."""
        self._session_stats.unsubscribe()
        self._menu_vars.clear()
        super().destroy()
        with _OVERLAY_LOCK:
            global _OVERLAY_INSTANCE
            if _OVERLAY_INSTANCE is self:
                _OVERLAY_INSTANCE = None

    def _apply_loaded_settings(self):
        self.x, self.y = self.settings["x"], self.settings["y"]
        self.font_size = self.settings["font_size"]
        self.next_boss_name = self.settings["next_boss_name"]
        self.orientation = self.settings["orientation"]
        self.locked = self.settings["locked"]
        self.font_family = self.settings["font_family"]
        self.capture_gold_stats = self.settings["capture_gold_stats"]
        self.capture_exp_stats = self.settings["capture_exp_stats"]

        # Assign all show_ attributes
        for k in self.settings:
            if k.startswith("show_"):
                setattr(self, k, self.settings[k])

        self.wb_reference = self.settings["wb_reference"]

        # In-memory synced data
        self.synced_wb = None
        self.synced_legion = None
        self.synced_helltide = None

        stats = SessionStats()
        self._gold_initialized = self.capture_gold_stats and stats.last_gold is not None
        self._exp_initialized = self.capture_exp_stats and stats.last_exp is not None

    def _save_settings(self):
        updates: dict[str, Any] = {
            "x": self.winfo_x(),
            "y": self.winfo_y(),
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
            except Exception:
                break
        return False

    def _setup_ui(self):
        self.labels_to_resize = []
        colors = get_filter_colors()
        self.frame = tk.Frame(self, bg=CARD_BG, highlightthickness=1, highlightbackground=colors.matched)
        self.frame.pack(padx=5, pady=5)

        self.wb_group = tk.Frame(self.frame, bg=CARD_BG)
        lbl_wb = tk.Label(
            self.wb_group, text="World Boss:", bg=CARD_BG, fg=colors.codex_upgrade, font=(self.font_family, self.font_size, "bold")
        )
        lbl_wb.pack(side="left")
        self.labels_to_resize.append(lbl_wb)
        self.wb_timer = tk.Label(
            self.wb_group, text="--:--:--", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.wb_timer.pack(side="left")
        self.labels_to_resize.append(self.wb_timer)

        self.legion_group = tk.Frame(self.frame, bg=CARD_BG)
        self.lbl_legion = tk.Label(
            self.legion_group,
            text="Legion:",
            bg=CARD_BG,
            fg=colors.matched,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.lbl_legion.pack(side="left")
        self.labels_to_resize.append(self.lbl_legion)
        self.legion_timer = tk.Label(
            self.legion_group, text="--:--:--", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.legion_timer.pack(side="left")
        self.labels_to_resize.append(self.legion_timer)

        self.ht_group = tk.Frame(self.frame, bg=CARD_BG)
        self.lbl_ht = tk.Label(
            self.ht_group,
            text="Helltide:",
            bg=CARD_BG,
            fg=colors.no_match,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.lbl_ht.pack(side="left")
        self.labels_to_resize.append(self.lbl_ht)
        self.ht_timer = tk.Label(
            self.ht_group, text="--:--:--", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.ht_timer.pack(side="left")
        self.labels_to_resize.append(self.ht_timer)

        self.stats_group = tk.Frame(self.frame, bg=CARD_BG)
        self.lbl_gph_title = tk.Label(
            self.stats_group, text="GPH:", bg=CARD_BG, fg=colors.matched, font=(self.font_family, self.font_size, "bold")
        )
        self.lbl_gph_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_gph_title)
        self.gph_value_label = tk.Label(
            self.stats_group, text="0", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.gph_value_label.pack(side="left")
        self.labels_to_resize.append(self.gph_value_label)

        self.lbl_total_gained_title = tk.Label(
            self.stats_group, text="|Gained:", bg=CARD_BG, fg=colors.matched, font=(self.font_family, self.font_size, "bold")
        )
        self.lbl_total_gained_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_total_gained_title)
        self.total_gained_value_label = tk.Label(
            self.stats_group, text="0", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.total_gained_value_label.pack(side="left")
        self.labels_to_resize.append(self.total_gained_value_label)

        self.exp_group = tk.Frame(self.frame, bg=CARD_BG)
        self.lbl_eph_title = tk.Label(
            self.exp_group, text="EPH:", bg=CARD_BG, fg=colors.matched, font=(self.font_family, self.font_size, "bold")
        )
        self.lbl_eph_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_eph_title)
        self.eph_value_label = tk.Label(
            self.exp_group, text="0", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.eph_value_label.pack(side="left")
        self.labels_to_resize.append(self.eph_value_label)

        self.lbl_total_exp_title = tk.Label(
            self.exp_group, text="|Exp:", bg=CARD_BG, fg=colors.matched, font=(self.font_family, self.font_size, "bold")
        )
        self.lbl_total_exp_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_total_exp_title)
        self.total_exp_value_label = tk.Label(
            self.exp_group, text="0", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.total_exp_value_label.pack(side="left")
        self.labels_to_resize.append(self.total_exp_value_label)

        self.t2l_group = tk.Frame(self.frame, bg=CARD_BG)
        self.lbl_t2l_title = tk.Label(
            self.t2l_group, text="T2L:", bg=CARD_BG, fg=colors.matched, font=(self.font_family, self.font_size, "bold")
        )
        self.lbl_t2l_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_t2l_title)
        self.t2l_value_label = tk.Label(
            self.t2l_group, text="-", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.t2l_value_label.pack(side="left")
        self.labels_to_resize.append(self.t2l_value_label)

        self.lbl_next_scan_title = tk.Label(
            self.t2l_group,
            text="|Next Scan:",
            bg=CARD_BG,
            fg=colors.matched,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.lbl_next_scan_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_next_scan_title)
        self.next_scan_value_label = tk.Label(
            self.t2l_group, text="Ready", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.next_scan_value_label.pack(side="left")
        self.labels_to_resize.append(self.next_scan_value_label)

        self._repack()
        self.geometry(f"+{self.x}+{self.y}")

    def _repack(self):
        """Recalculate component packing based on current settings."""
        LOGGER.debug(
            f"Repacking overlay. show_gold={self.show_gold}, _gold_initialized={self._gold_initialized}, show_gph={self.show_gph}, show_total_gold={self.show_total_gold}, show_exp={self.show_exp}, _exp_initialized={self._exp_initialized}, show_eph={self.show_eph}, show_total_exp={self.show_total_exp}, show_t2l={self.show_t2l}, show_next_scan={self.show_next_scan}"
        )
        # Hide everything first
        self.wb_group.pack_forget()
        self.legion_group.pack_forget()
        self.ht_group.pack_forget()
        self.stats_group.pack_forget()
        self.exp_group.pack_forget()
        self.t2l_group.pack_forget()

        side = "top" if self.orientation == "vertical" else "left"
        anchor = "w" if self.orientation == "vertical" else None

        if self.show_wb:
            self.wb_group.pack(side=side, anchor=anchor, padx=2)
        if self.show_legion:
            self.legion_group.pack(side=side, anchor=anchor, padx=2)
        if self.show_ht:
            self.ht_group.pack(side=side, anchor=anchor, padx=2)
        if self.capture_gold_stats and self._gold_initialized and (self.show_gph or self.show_total_gold):
            self._repack_gold_group()
            self.stats_group.pack(side=side, anchor=anchor, padx=2)
        if self.capture_exp_stats and self._exp_initialized:
            if self.show_eph or self.show_total_exp:
                self._repack_exp_group()
                self.exp_group.pack(side=side, anchor=anchor, padx=2)
            if self.show_t2l or self.show_next_scan:
                self._repack_t2l_group()
                self.t2l_group.pack(side=side, anchor=anchor, padx=2)

    def _repack_gold_group(self):
        self.lbl_gph_title.pack_forget()
        self.gph_value_label.pack_forget()
        self.lbl_total_gained_title.pack_forget()
        self.total_gained_value_label.pack_forget()
        count = 0
        if self.show_gph:
            self.lbl_gph_title.config(text="GPH:")
            self.lbl_gph_title.pack(side="left")
            self.gph_value_label.pack(side="left")
            count += 1
        if self.show_total_gold:
            self.lbl_total_gained_title.config(text="|Gained:" if count > 0 else "Gained:")
            self.lbl_total_gained_title.pack(side="left")
            self.total_gained_value_label.pack(side="left")

    def _repack_exp_group(self):
        self.lbl_eph_title.pack_forget()
        self.eph_value_label.pack_forget()
        self.lbl_total_exp_title.pack_forget()
        self.total_exp_value_label.pack_forget()
        count = 0
        if self.show_eph:
            self.lbl_eph_title.config(text="EPH:")
            self.lbl_eph_title.pack(side="left")
            self.eph_value_label.pack(side="left")
            count += 1
        if self.show_total_exp:
            self.lbl_total_exp_title.config(text="|Exp:" if count > 0 else "Exp:")
            self.lbl_total_exp_title.pack(side="left")
            self.total_exp_value_label.pack(side="left")
            count += 1

    def _repack_t2l_group(self):
        self.lbl_t2l_title.pack_forget()
        self.t2l_value_label.pack_forget()
        self.lbl_next_scan_title.pack_forget()
        self.next_scan_value_label.pack_forget()
        count = 0
        if self.show_t2l:
            self.lbl_t2l_title.config(text="T2L:")
            self.lbl_t2l_title.pack(side="left")
            self.t2l_value_label.pack(side="left")
            count += 1
        if self.show_next_scan:
            self.lbl_next_scan_title.config(text="|Next Scan:" if count > 0 else "Next Scan:")
            self.lbl_next_scan_title.pack(side="left")
            self.next_scan_value_label.pack(side="left")

    def _toggle_orientation(self):
        self.orientation = "vertical" if self.orientation == "horizontal" else "horizontal"
        self.frame.config(highlightbackground=get_filter_colors().matched)
        self._repack()
        self._save_settings()

    def _create_toggle_btn(self, parent, label_text, attr_name, callback=None):
        """Creates a toggle button that updates state and color immediately."""
        is_active = getattr(self, attr_name)
        colors = get_filter_colors()

        btn = tk.Button(
            parent,
            text=label_text,
            bg=CARD_BG,
            fg=colors.matched if is_active else MUTED,
            font=(self.font_family, self.font_size, "bold"),
            activebackground=colors.matched,
            activeforeground=CARD_BG,
            bd=0,
            padx=10,
            pady=5,
            anchor="w",
        )

        def _on_click():
            new_val = not getattr(self, attr_name)
            setattr(self, attr_name, new_val)
            btn.config(fg=colors.matched if new_val else MUTED)
            if callback:
                callback()
            self._repack()
            self._save_settings()

        btn.config(command=_on_click)
        btn.pack(fill="x")
        return btn

    def _create_config_toggle_btn(self, parent, label_text, config_key, callback=None):
        """Creates a toggle button for settings stored in QSettings."""
        is_active = self.settings.get(config_key, False)

        btn = tk.Button(
            parent,
            text=label_text,
            bg=CARD_BG,
            fg=ACTIVE_GREEN if is_active else MUTED,
            font=(self.font_family, self.font_size, "bold"),
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            bd=0,
            padx=10,
            pady=5,
            anchor="w",
        )

        def _on_click():
            new_val = not self.settings.get(config_key, False)
            save_info_settings({config_key: new_val})
            self.settings[config_key] = new_val
            if callback:
                callback()
            else:
                btn.config(fg=ACTIVE_GREEN if new_val else MUTED)
            self._repack()
            self._save_settings()

        btn.config(command=_on_click)
        btn.pack(fill="x")
        return btn

    def _create_radio_button(
        self, parent, label_text, current_value, target_value, on_select_callback, config_key=None
    ):
        """Creates a radio-style button that visually indicates selection."""
        is_selected = current_value == target_value
        fg_color = ACTIVE_GREEN if is_selected else MUTED

        btn = tk.Button(
            parent,
            text=f"● {label_text}" if is_selected else f"  {label_text}",
            bg=CARD_BG,
            fg=fg_color,
            font=(self.font_family, self.font_size, "bold"),
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            bd=0,
            padx=20,  # Indent further for radio items
            pady=5,
            anchor="w",
        )

        def _on_click():
            on_select_callback(target_value)
            if config_key:
                save_info_settings({config_key: target_value})
                self.settings[config_key] = target_value
            self._repack()
            self._save_settings()
            # Rebuild the entire popup to update all radio buttons in the group
            if self._settings_popup and self._settings_popup.winfo_exists():
                self._settings_popup.destroy()
            self._show_context_menu(event=None)  # Re-open at last position

        btn.config(command=_on_click)
        btn.pack(fill="x")
        return btn

    def _create_submenu_button(
        self, parent: tk.Misc, label_text: str, submenu_id: str, content_builder: Callable[[tk.Toplevel], None]
    ):
        """Creates a button that opens a cascading Toplevel submenu to its side."""
        btn = tk.Button(
            parent,
            text=f"{label_text} ▶",  # Default to collapsed
            bg=CARD_BG,
            fg=TEXT,
            font=(self.font_family, self.font_size, "bold"),
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            bd=0,
            padx=10,
            pady=5,
            anchor="w",
            command=lambda: self._open_submenu(btn, submenu_id, content_builder),
        )
        btn.pack(fill="x")
        return btn

    def _on_popup_focus_out(self, event):
        """Delayed check to see if focus left the entire settings UI family."""
        # Tiny delay to allow the new focus widget to be determined by the system
        self.after(100, self._check_popup_focus)

    def _check_popup_focus(self):
        """Destroy popups only if focus has moved entirely out of the settings window family."""
        if not self._settings_popup or not self._settings_popup.winfo_exists():
            return

        focus = self.focus_get()
        if focus:
            # Check if focus is in main popup
            if self._is_descendant(focus, self._settings_popup):
                return
            # Check if focus is in any open submenu
            for sub in self._open_submenus.values():
                if sub.winfo_exists() and self._is_descendant(focus, sub):
                    return

        # Focus is truly gone, cleanup everything
        self._close_all_submenus()
        if self._settings_popup and self._settings_popup.winfo_exists():
            self._settings_popup.destroy()

    def _open_submenu(self, parent_btn: tk.Button, submenu_id: str, content_builder: Callable[[tk.Toplevel], None]):
        """Opens a cascading Toplevel submenu to the side of the parent button."""
        # Close any other open submenus at this level
        for key, existing_popup in list(self._open_submenus.items()):
            if key != submenu_id and existing_popup.winfo_exists() and existing_popup.master is parent_btn.master:
                existing_popup.destroy()
                del self._open_submenus[key]

        if submenu_id in self._open_submenus and self._open_submenus[submenu_id].winfo_exists():
            # Submenu is already open, close it
            self._open_submenus[submenu_id].destroy()
            del self._open_submenus[submenu_id]
            return

        # Create the submenu
        submenu_popup = tk.Toplevel(parent_btn.master)
        submenu_popup.overrideredirect(True)
        submenu_popup.attributes("-topmost", True)
        submenu_popup.configure(bg=CARD_BG, highlightthickness=1, highlightbackground=ACCENT)

        # Build content inside the submenu_popup
        content_builder(submenu_popup)

        # Ensure parent button's geometry is updated before querying its position
        parent_btn.update_idletasks()
        submenu_popup.update_idletasks()

        # Position to the right of the parent button
        x = parent_btn.winfo_rootx() + parent_btn.winfo_width() + 5  # 5 pixels offset to the right
        y = parent_btn.winfo_rooty()

        # Simple boundary check: if it goes off screen to the right, pop to the left
        screen_w = self.winfo_screenwidth()
        if x + submenu_popup.winfo_reqwidth() > screen_w:
            x = parent_btn.winfo_rootx() - submenu_popup.winfo_reqwidth() - 5

        submenu_popup.geometry(f"+{x}+{y}")
        submenu_popup.lift()

        # Bind events
        submenu_popup.bind("<FocusOut>", self._on_popup_focus_out)
        submenu_popup.bind(
            "<Escape>",
            lambda _: (self._settings_popup.destroy() if self._settings_popup else None, self._close_all_submenus()),
        )

        self._open_submenus[submenu_id] = submenu_popup

        # Give focus to the new submenu
        submenu_popup.focus_set()

    def _show_context_menu(self, event):
        """Create and display a persistent settings popup."""
        if self._settings_popup and self._settings_popup.winfo_exists():
            self._settings_popup.destroy()

        if event:
            self._last_menu_pos = (event.x_root, event.y_root)

        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=CARD_BG, highlightthickness=1, highlightbackground=ACCENT)
        self._settings_popup = popup

        # Header
        header = tk.Label(
            popup, text="SETTINGS", bg=ACCENT, fg=CARD_BG, font=(self.font_family, self.font_size, "bold")
        )
        header.pack(fill="x")

        # Visibility Section
        self._create_toggle_btn(popup, "World Boss", "show_wb")
        self._create_toggle_btn(popup, "Legion", "show_legion")
        self._create_toggle_btn(popup, "Helltide", "show_ht")

        tk.Frame(popup, height=1, bg=ACCENT).pack(fill="x", pady=2)

        # Gold Stats Submenu (Cascading)
        def build_gold_submenu_content(submenu_frame):
            def update_dependent_widgets():
                is_tracking = self.capture_gold_stats
                state = tk.NORMAL if is_tracking else tk.DISABLED
                btn_gph.config(state=state, fg=ACTIVE_GREEN if (is_tracking and self.show_gph) else MUTED)
                btn_gained.config(state=state, fg=ACTIVE_GREEN if (is_tracking and self.show_total_gold) else MUTED)

            self._create_toggle_btn(
                submenu_frame, "Track Gold", "capture_gold_stats", callback=update_dependent_widgets
            )

            tk.Frame(submenu_frame, height=1, bg=ACCENT).pack(fill="x", pady=2)

            btn_gph = self._create_toggle_btn(submenu_frame, "Show Gold Per Hour", "show_gph")
            btn_gained = self._create_toggle_btn(submenu_frame, "Show Gold Gained", "show_total_gold")

            update_dependent_widgets()

        self._create_submenu_button(popup, "Gold Config", "gold_stats_submenu", build_gold_submenu_content).pack(
            fill="x"
        )

        # Exp Config Submenu (Cascading)
        def build_exp_submenu_content(submenu_frame):
            def update_dependent_widgets():
                is_tracking = self.capture_exp_stats
                state = tk.NORMAL if is_tracking else tk.DISABLED

                btn_eph.config(state=state, fg=ACTIVE_GREEN if (is_tracking and self.show_eph) else MUTED)
                btn_gained.config(state=state, fg=ACTIVE_GREEN if (is_tracking and self.show_total_exp) else MUTED)
                btn_t2l.config(state=state, fg=ACTIVE_GREEN if (is_tracking and self.show_t2l) else MUTED)
                btn_next.config(state=state, fg=ACTIVE_GREEN if (is_tracking and self.show_next_scan) else MUTED)
                btn_inv.config(
                    state=state,
                    fg=ACTIVE_GREEN if (is_tracking and self.settings.get("check_exp_on_inventory_open")) else MUTED,
                )

                btn_age.config(state=state, fg=TEXT if is_tracking else MUTED)
                btn_pick.config(state=state, fg=TEXT if is_tracking else MUTED)
                btn_reset_pos.config(state=state, fg=TEXT if is_tracking else MUTED)

                if self.settings.get("exp_bar_pos") is None:
                    btn_reset_pos.pack_forget()
                else:
                    btn_reset_pos.pack(fill="x")

            self._create_toggle_btn(submenu_frame, "Track Exp", "capture_exp_stats", callback=update_dependent_widgets)

            tk.Frame(submenu_frame, height=1, bg=ACCENT).pack(fill="x", pady=2)

            btn_eph = self._create_toggle_btn(submenu_frame, "Show EXP Per Hour", "show_eph")
            btn_gained = self._create_toggle_btn(submenu_frame, "Show EXP Gained", "show_total_exp")
            btn_t2l = self._create_toggle_btn(submenu_frame, "Show Time to Level", "show_t2l")
            btn_next = self._create_toggle_btn(submenu_frame, "Show Next Scan", "show_next_scan")

            tk.Frame(submenu_frame, height=1, bg=ACCENT).pack(fill="x", pady=2)

            btn_inv = self._create_config_toggle_btn(
                submenu_frame, "Inv Open (Capture EXP)", "check_exp_on_inventory_open"
            )

            def build_exp_age_sub_submenu_content(sub_submenu_frame):
                for label, val in [
                    ("Never", -1),
                    ("0m", 0),
                    ("3m", 3),
                    ("5m", 5),
                    ("10m", 10),
                    ("30m", 30),
                    ("60m", 60),
                ]:
                    self._create_radio_button(
                        sub_submenu_frame,
                        label,
                        self.settings["exp_age_before_refresh"],
                        val,
                        lambda _: None,
                        config_key="exp_age_before_refresh",
                    ).pack(fill="x")

            btn_age = self._create_submenu_button(
                submenu_frame, "EXP Capture Time", "exp_age_sub_submenu", build_exp_age_sub_submenu_content
            )

            tk.Frame(submenu_frame, height=1, bg=ACCENT).pack(fill="x", pady=2)

            btn_pick = tk.Button(
                submenu_frame,
                text="Configure EXP Bar Position",
                bg=CARD_BG,
                fg=TEXT,
                bd=0,
                anchor="w",
                padx=10,
                pady=5,
                font=(self.font_family, self.font_size, "bold"),
                activebackground=ACCENT,
                activeforeground=CARD_BG,
                command=lambda: (
                    self._pick_exp_bar_pos(),
                    self._settings_popup.destroy() if self._settings_popup else None,
                    self._close_all_submenus(),
                ),
            )
            btn_pick.pack(fill="x")

            btn_reset_pos = tk.Button(
                submenu_frame,
                text="Reset EXP Bar Position",
                bg=CARD_BG,
                fg=TEXT,
                bd=0,
                anchor="w",
                padx=10,
                pady=5,
                font=(self.font_family, self.font_size, "bold"),
                activebackground=ACCENT,
                activeforeground=CARD_BG,
                command=lambda: (
                    self._reset_exp_bar_pos(),
                    self._settings_popup.destroy() if self._settings_popup else None,
                    self._close_all_submenus(),
                ),
            )
            btn_reset_pos.pack(fill="x")

            update_dependent_widgets()

        self._create_submenu_button(popup, "Exp Config", "exp_stats_submenu", build_exp_submenu_content).pack(fill="x")

        # Reset Stats Submenu (Cascading)
        def build_reset_submenu_content(submenu_frame):
            tk.Button(
                submenu_frame,
                text="Reset Gold",
                bg=CARD_BG,
                fg=TEXT,
                bd=0,
                anchor="w",
                padx=10,
                pady=5,
                font=(self.font_family, self.font_size, "bold"),
                activebackground=ACCENT,
                activeforeground=CARD_BG,
                command=self._reset_gold_stats,
            ).pack(fill="x")
            tk.Button(
                submenu_frame,
                text="Reset Exp",
                bg=CARD_BG,
                fg=TEXT,
                bd=0,
                anchor="w",
                padx=10,
                pady=5,
                font=(self.font_family, self.font_size, "bold"),
                activebackground=ACCENT,
                activeforeground=CARD_BG,
                command=self._reset_exp_stats,
            ).pack(fill="x")

        self._create_submenu_button(popup, "Reset Stats", "reset_stats_submenu", build_reset_submenu_content).pack(
            fill="x"
        )

        tk.Frame(popup, height=1, bg=ACCENT).pack(fill="x", pady=2)

        # UI Adjustments
        tk.Button(
            popup,
            text=f"Orientation: {self.orientation.title()}",
            bg=CARD_BG,
            fg=TEXT,
            bd=0,
            anchor="w",
            padx=10,
            pady=5,
            font=(self.font_family, self.font_size),
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            command=lambda: (
                self._toggle_orientation(),
                self._settings_popup.destroy(),
                self._show_context_menu(event=None),
            ),
        ).pack(fill="x")
        tk.Button(
            popup,
            text="Increase Size (+)",
            bg=CARD_BG,
            fg=TEXT,
            bd=0,
            anchor="w",
            padx=10,
            pady=5,
            font=(self.font_family, self.font_size),
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            command=lambda: (self._change_size(2), self._settings_popup.destroy(), self._show_context_menu(event=None)),
        ).pack(fill="x")
        tk.Button(
            popup,
            text="Decrease Size (-)",
            bg=CARD_BG,
            fg=TEXT,
            bd=0,
            anchor="w",
            padx=10,
            pady=5,
            font=(self.font_family, self.font_size),
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            command=lambda: (
                self._change_size(-2),
                self._settings_popup.destroy(),
                self._show_context_menu(event=None),
            ),
        ).pack(fill="x")

        # Font Submenu
        def build_font_submenu_content(submenu_frame):
            for font_name in self.FONT_CHOICES:
                self._create_radio_button(
                    submenu_frame, font_name, self.font_family, font_name, self._change_font_family
                ).pack(fill="x")

        self._create_submenu_button(popup, "Font", "font_submenu", build_font_submenu_content).pack(fill="x")

        tk.Frame(popup, height=1, bg=ACCENT).pack(fill="x", pady=2)

        # System Actions
        for label, cmd in [
            ("Auto Sync Timers", self._auto_sync),
            ("Lock Position", self._toggle_lock),
            ("Close Overlay", request_close),
        ]:
            btn = tk.Button(
                popup,
                text=label,
                bg=CARD_BG,
                fg=TEXT,
                bd=0,
                anchor="w",
                padx=10,
                pady=5,
                font=(self.font_family, self.font_size),
                activebackground=ACCENT,
                activeforeground=CARD_BG,
                command=lambda c=cmd, lbl=label: (
                    c(),
                    self._settings_popup.destroy(),
                    self._show_context_menu(event=None) if lbl != "Close Overlay" else None,
                ),
            )
            btn.pack(fill="x")

        # Position the popup at the mouse click
        popup.geometry(f"+{self._last_menu_pos[0]}+{self._last_menu_pos[1]}")

        # Auto-close logic
        popup.bind("<FocusOut>", self._on_popup_focus_out)  # Use the family focus out handler
        popup.bind("<Escape>", lambda _: (popup.destroy(), self._close_all_submenus()))  # Escape still closes all
        popup.focus_set()

    def _close_all_submenus(self):
        for key, existing_popup in list(self._open_submenus.items()):
            if existing_popup.winfo_exists():
                existing_popup.destroy()
            del self._open_submenus[key]

    def _toggle_lock(self):
        self.locked = not self.locked
        self._on_lock_changed()
        self._save_settings()

    def _on_lock_changed(self):
        if self.locked:
            self.config(cursor="")

    def _reset_gold_stats(self):
        SessionStats().reset_gold()
        self._gold_initialized = False
        self.update_stats(gph=0, total_gained=0)
        self._repack()

    def _change_font_family(self, new_font_family):
        self.font_family = new_font_family
        for lbl in self.labels_to_resize:
            lbl.config(font=(self.font_family, self.font_size, "bold"))
        self._save_settings()

    def _reset_exp_stats(self):
        SessionStats().reset_exp()
        self._exp_initialized = False
        self.update_stats(eph=0, total_exp=0, t2l="-")
        self._repack()

    def _pick_exp_bar_pos(self):
        """Show a fullscreen overlay to capture the experience bar position via drag."""
        picker = tk.Toplevel(self)
        picker.attributes("-fullscreen", True)
        picker.attributes("-alpha", 0.5)
        picker.attributes("-topmost", True)
        picker.config(bg="black", cursor="cross")

        canvas = tk.Canvas(picker, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        msg = "DRAG ACROSS YOUR EXPERIENCE BAR\n(Escape to cancel)"
        canvas.create_text(
            picker.winfo_screenwidth() // 2,
            picker.winfo_screenheight() // 2,
            text=msg,
            font=(self.font_family, 20, "bold"),
            fill=ACTIVE_GREEN,
        )

        state = {"start": None, "line": None}

        def on_press(event):
            state["start"] = (event.x_root, event.y_root)
            state["line"] = canvas.create_line(event.x, event.y, event.x, event.y, fill=ACTIVE_GREEN, width=3)

        def on_motion(event):
            if state["line"]:
                canvas.coords(state["line"], state["start"][0], state["start"][1], event.x, event.y)

        def on_release(event):
            win_start = Cam().monitor_to_window(state["start"])
            win_end = Cam().monitor_to_window((event.x_root, event.y_root))
            val = f"({int(win_start[0])}, {int(win_start[1])}, {int(win_end[0])}, {int(win_end[1])})"
            save_info_settings({"exp_bar_pos": val})
            self.settings["exp_bar_pos"] = val
            picker.destroy()
            LOGGER.info(f"Custom EXP bar selection set to {val}")

        picker.bind("<Button-1>", on_press)
        picker.bind("<B1-Motion>", on_motion)
        picker.bind("<ButtonRelease-1>", on_release)
        picker.bind("<Escape>", lambda _: picker.destroy())

    def _reset_exp_bar_pos(self):
        """Reset the custom experience bar position to default."""
        save_info_settings({"exp_bar_pos": "None"})
        self.settings["exp_bar_pos"] = None
        LOGGER.info("Experience bar position reset to default calculation")

    def _bind_events(self):
        self._recursive_bind_drag(self)

    def _recursive_bind_drag(self, widget):
        """Bind drag events to a widget and all its children recursively."""
        widget.bind("<Button-1>", self._start_drag, add="+")
        widget.bind("<B1-Motion>", self._do_drag, add="+")
        widget.bind("<ButtonRelease-1>", self._stop_drag, add="+")
        widget.bind("<Button-3>", self._show_context_menu, add="+")
        for child in widget.winfo_children():
            self._recursive_bind_drag(child)

    def _change_size(self, delta):
        self.font_size = max(8, min(48, self.font_size + delta))
        for lbl in self.labels_to_resize:
            lbl.config(font=(self.font_family, self.font_size, "bold"))
        self._save_settings()

    def _start_drag(self, event):
        if self.locked:
            return
        self.config(cursor="fleur")
        # Calculate and store the fixed offset from the window's top-left to the mouse click
        self._drag_offset_x = event.x_root - self.winfo_x()
        self._drag_offset_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        if self.locked or not hasattr(self, "_drag_offset_x"):
            return
        # Set the geometry based on current mouse position minus the original offset
        x = int(event.x_root - self._drag_offset_x)
        y = int(event.y_root - self._drag_offset_y)
        self.geometry(f"+{x}+{y}")

    def _stop_drag(self, event):
        self.config(cursor="")
        self._save_settings()

    def _auto_sync(self):
        """Fetch schedule from helltides.com and sync the timer."""
        threading.Thread(target=self._fetch_schedule, daemon=True).start()

    def _fetch_schedule(self):
        try:
            url = "https://helltides.com/schedule"
            with httpx.Client(timeout=10) as client:
                response = client.get(url)
                if response.status_code == 200:
                    text = response.text
                    now = datetime.datetime.now(datetime.UTC)

                    # Regex for World Bosses: "BossName","world_boss","YYYY-MM-DDTHH:MM:SS.000Z"
                    wb_pattern = r"\"(Ashava|Avarice|Wandering Death)\",\"world_boss\",\"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\""
                    wb_matches = re.findall(wb_pattern, text)

                    # Regex for Legions: "legion","YYYY-MM-DDTHH:MM:SS.000Z"
                    legion_pattern = r"\"legion\",\"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\""
                    legion_matches = re.findall(legion_pattern, text)

                    # Regex for Helltides: "YYYY-MM-DDTHH:MM:SS.000Z","helltide"
                    ht_pattern = r"\"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\",\"helltide\""
                    ht_matches = re.findall(ht_pattern, text)

                    # Process World Bosses
                    best_wb = None
                    for name, dt_str in wb_matches:
                        dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.UTC)
                        if dt > now and (best_wb is None or dt < best_wb[0]):
                            best_wb = (dt, name)

                    if best_wb:
                        self.synced_wb = best_wb
                        self.wb_reference = best_wb[0]
                        self.next_boss_name = best_wb[1]
                        self._save_settings()
                        LOGGER.info(f"Auto-synced World Boss: {best_wb[1]} at {best_wb[0]}")

                    # Process Legions
                    best_legion = None
                    for dt_str in legion_matches:
                        dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.UTC)
                        if dt > now and (best_legion is None or dt < best_legion):
                            best_legion = dt
                    if best_legion:
                        self.synced_legion = best_legion
                        LOGGER.info(f"Auto-synced Legion: {best_legion}")

                    # Process Helltides
                    # Find the helltide start time for the current or next cycle.
                    # Current seasons have helltides starting every hour.
                    latest_start = None
                    for dt_str in ht_matches:
                        dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.UTC)
                        if dt <= now:
                            if latest_start is None or dt > latest_start:
                                latest_start = dt
                        elif dt > now and latest_start is None:
                            latest_start = dt
                    if latest_start:
                        self.synced_helltide = latest_start
                        LOGGER.info(f"Auto-synced Helltide: {latest_start}")

                    # Schedule the update on the UI thread to avoid cross-thread GUI errors
                    def _safe_update():
                        if self.winfo_exists():
                            self._update_timers()

                    self.after(0, _safe_update)
        except Exception as e:
            LOGGER.error(f"Failed to auto-sync from helltides.com: {e}")

    def _update_timers(self):
        if not self.winfo_exists():
            return
        now = datetime.datetime.now(datetime.UTC)
        self._flash_toggle = not self._flash_toggle

        def get_flash_color(seconds, base_color, threshold=300):
            if 0 < seconds < threshold and not self._flash_toggle:
                return TEXT
            if 0 < seconds < threshold:
                return WARNING_ORANGE
            return base_color

        # --- World Boss ---

        # World Boss
        if self.synced_wb and self.synced_wb[0] > now:
            next_wb = self.synced_wb[0]
        else:
            # Fallback to 3.5h interval from reference
            wb_interval = datetime.timedelta(hours=3.5)
            time_since_wb = now - self.wb_reference
            intervals_passed = time_since_wb // wb_interval
            next_wb = self.wb_reference + (intervals_passed + 1) * wb_interval
            if next_wb < now:
                next_wb += wb_interval

        wb_remaining = next_wb - now
        if wb_remaining.total_seconds() < 0:
            self.wb_timer.config(text="ACTIVE")
            self.wb_timer.config(fg=ACTIVE_GREEN)  # Active WB is green
        else:
            self.wb_timer.config(
                text=str(wb_remaining).split(".")[0], fg=get_flash_color(wb_remaining.total_seconds(), ACTIVE_GREEN)
            )
        # --- Legion ---
        # Legion
        if self.synced_legion and self.synced_legion > now:
            legion_remaining = self.synced_legion - now
        else:
            # Fallback to 25m interval
            legion_interval = datetime.timedelta(minutes=25)
            legion_ref = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
            time_since_legion = now - legion_ref
            legion_passed = time_since_legion // legion_interval
            next_legion = legion_ref + (legion_passed + 1) * legion_interval
            legion_remaining = next_legion - now
        self.legion_timer.config(
            text=str(legion_remaining).split(".")[0], fg=get_flash_color(legion_remaining.total_seconds(), ACTIVE_GREEN)
        )

        # --- Helltide ---
        # Helltide
        # Diablo 4 Helltides cycle every hour: 55 minutes active, 5 minutes break.
        ht_ref = self.synced_helltide or now.replace(minute=0, second=0, microsecond=0)
        diff = (now - ht_ref).total_seconds()

        if diff < 0:
            # Synced reference is in the future
            ht_rem = ht_ref - now
            self.ht_timer.config(
                text=str(ht_rem).split(".")[0], fg=get_flash_color(ht_rem.total_seconds(), ACTIVE_GREEN, 60)
            )
        else:
            # Normalized position in the infinite 1-hour cycle
            cycle_pos = diff % 3600
            if cycle_pos < 3300:
                # Active (0-55 mins)
                rem = datetime.timedelta(seconds=int(3300 - cycle_pos))
                self.ht_timer.config(
                    text=str(rem).split(".")[0], fg=get_flash_color(rem.total_seconds(), PROGRESS_YELLOW, 300)
                )
            else:
                # Break / Warning (55-60 mins)
                rem = datetime.timedelta(seconds=int(3600 - cycle_pos))
                self.ht_timer.config(
                    text=str(rem).split(".")[0], fg=get_flash_color(rem.total_seconds(), ACTIVE_GREEN, 60)
                )

        # --- Next Scan Cooldown ---
        with suppress(Exception):
            info_conf = load_info_settings()
            if not info_conf["check_exp_on_inventory_open"]:
                self.next_scan_value_label.config(text="Off")
            elif info_conf["exp_age_before_refresh"] == -1:
                self.next_scan_value_label.config(text="Never")
            elif SessionStats().last_exp is None:
                self.next_scan_value_label.config(text="Ready")
            else:
                remaining = (info_conf["exp_age_before_refresh"] * 60) - (
                    time.time() - InventoryExpTracker().last_hover_time
                )
                if remaining <= 0:
                    self.next_scan_value_label.config(text="Ready")
                else:
                    m, s = divmod(int(remaining), 60)
                    self.next_scan_value_label.config(text=f"{m}m {s}s" if m > 0 else f"{s}s")

        self.after(1000, self._update_timers)

    def update_stats(
        self,
        gph: int | None = None,
        total_gained: int | None = None,
        eph: int | None = None,
        total_exp: int | None = None,
        t2l: str | None = None,
    ):
        """Update the gold and experience statistics display."""
        repack_needed = False
        if gph is not None and self.capture_gold_stats:
            self.gph_value_label.config(text=f"{gph:,}")
            if not self._gold_initialized:
                self._gold_initialized = True
                repack_needed = True
        if total_gained is not None and self.capture_gold_stats:
            self.total_gained_value_label.config(text=f"{total_gained:,}")
            if not self._gold_initialized:
                self._gold_initialized = True
                repack_needed = True
        if eph is not None and self.capture_exp_stats:
            self.eph_value_label.config(text=f"{eph:,}")
            if not self._exp_initialized:
                self._exp_initialized = True
                repack_needed = True
        if total_exp is not None and self.capture_exp_stats:
            self.total_exp_value_label.config(text=f"{total_exp:,}")
            if not self._exp_initialized:
                self._exp_initialized = True
                repack_needed = True
        if t2l is not None and self.capture_exp_stats:
            self.t2l_value_label.config(text=t2l)

        if repack_needed:
            self._repack()
            self.update_idletasks()


def run_boss_timer_overlay():
    global _OVERLAY_INSTANCE
    with _OVERLAY_LOCK:
        if _OVERLAY_INSTANCE is not None:
            LOGGER.warning("Info Panel overlay is already running.")
            return

    root = tk.Tk()
    root.withdraw()
    overlay = BossTimerOverlay(root)
    with _OVERLAY_LOCK:
        _OVERLAY_INSTANCE = overlay
    root.mainloop()
