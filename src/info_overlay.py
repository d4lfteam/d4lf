from __future__ import annotations
import datetime
from dataclasses import dataclass
import logging
import tkinter as tk
from pathlib import Path
import configparser
import httpx
import re
import threading
import time
from contextlib import suppress
from typing import Any, Callable, TYPE_CHECKING
from src.config.loader import IniConfigLoader
from src.config.helper import singleton
from src.tts import Publisher
from src.utils.custom_mouse import mouse
from src.cam import Cam
if TYPE_CHECKING:
    pass

@dataclass(frozen=True)
class InfoStat:
    name: str
    value: int
    max_value: int | None = None

LOGGER = logging.getLogger(__name__)

_OVERLAY_INSTANCE: BossTimerOverlay | None = None
_OVERLAY_LOCK = threading.RLock()
_OVERLAY_THREAD: threading.Thread | None = None
_LAST_TOGGLE_TIME = 0

_BUSY_CHECKER: Callable[[], bool] = lambda: False

def set_busy_checker(checker: Callable[[], bool]):
    """Hook for the script handler to provide a busy state check."""
    global _BUSY_CHECKER
    _BUSY_CHECKER = checker

# =============================================================================
# SETTINGS PERSISTENCE (PARAGON STYLE)
# =============================================================================

def _params_ini_path() -> Path:
    p = Path.home() / ".d4lf"
    p.mkdir(parents=True, exist_ok=True)
    return p / "params.ini"

def load_info_settings() -> dict[str, Any]:
    """Load info overlay and experience tracking settings from params.ini."""
    ini = _params_ini_path()
    p = configparser.ConfigParser()
    if ini.exists():
        p.read(ini, encoding="utf-8")
    sec = p["info_overlay"] if p.has_section("info_overlay") else {}

    def parse_bool(k: str, default: bool) -> bool:
        v = sec.get(k, str(default)).lower()
        return v in ("true", "1", "yes", "on")

    def parse_int(k: str, default: int) -> int:
        try:
            return int(sec.get(k, str(default)))
        except ValueError:
            return default

    def parse_tuple(k: str) -> tuple[int, ...] | None:
        v = sec.get(k)
        if not v or v.lower() == "none":
            return None
        try:
            return tuple(int(x.strip()) for x in v.strip("()").replace(",", " ").split())
        except Exception:
            return None

    # Boss Timer UI Settings
    settings = {
        "x": parse_int("x", 100),
        "y": parse_int("y", 100),
        "font_size": parse_int("font_size", 14),
        "wb_reference": sec.get("wb_reference", "2024-01-01 00:00:00"),
        "next_boss_name": sec.get("next_boss_name", "Unknown"),
        "orientation": sec.get("orientation", "horizontal"),
        "show_wb": parse_bool("show_wb", True),
        "show_legion": parse_bool("show_legion", True),
        "show_ht": parse_bool("show_ht", True),
        "show_gold": parse_bool("show_gold", True),
        "show_gph": parse_bool("show_gph", True),
        "show_total_gold": parse_bool("show_total_gold", True),
        "show_exp": parse_bool("show_exp", True),
        "show_eph": parse_bool("show_eph", True),
        "show_total_exp": parse_bool("show_total_exp", True),
        "show_t2l": parse_bool("show_t2l", True),
        "show_next_scan": parse_bool("show_next_scan", True),
        "locked": parse_bool("locked", False),
        # Experience/Tracking Settings (Moved from GeneralModel)
        "check_exp_on_inventory_open": parse_bool("check_exp_on_inventory_open", True),
        "exp_age_before_refresh": parse_int("exp_age_before_refresh", 5),
        "exp_bar_pos": parse_tuple("exp_bar_pos"),
    }
    return settings

def save_info_settings(values: dict[str, Any]) -> None:
    """Persist settings to the [info_overlay] section of params.ini."""
    ini = _params_ini_path()
    p = configparser.ConfigParser()
    if ini.exists():
        p.read(ini, encoding="utf-8")
    if not p.has_section("info_overlay"):
        p.add_section("info_overlay")
    
    for k, v in values.items():
        p["info_overlay"][k] = str(v)
        
    with ini.open("w", encoding="utf-8") as f:
        p.write(f)

def get_info_setting(key: str, default: Any = None) -> Any:
    """Quick access to a specific info overlay setting."""
    return load_info_settings().get(key, default)

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

    def _parse_stat(self, raw_line: str) -> InfoStat | None:
        # Handle Gold statistics from raw TTS string (e.g., '2,225,130,802 Gold')
        if (
            "gold" in raw_line.lower()
            and not any(x in raw_line.lower() for x in ["sell value", "repair", "cost", "price", "buy", "fee", "spent", "purchase"])
            and (match := re.search(r"([0-9,.]+)\s+Gold", raw_line, re.IGNORECASE))
        ):
            raw_val = re.sub(r"\D", "", match.group(1))
            if raw_val:
                return InfoStat(name="gold_balance", value=int(raw_val))
        # Handle Experience statistics (e.g., 'Level 209 Experience: 55,843,725 / 74,304,757')
        elif "experience" in raw_line.lower() and (match := re.search(r"Experience:\s+([0-9,.]+)\s+/\s+([0-9,.]+)", raw_line, re.IGNORECASE)):
            raw_val = re.sub(r"\D", "", match.group(1))
            raw_mx = re.sub(r"\D", "", match.group(2))
            if raw_val and raw_mx:
                return InfoStat(name="experience_gain", value=int(raw_val), max_value=int(raw_mx))
        return None

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
        if hasattr(self, "last_gold"): self.last_gold = None
        LOGGER.info("Gold session stats reset")

    def reset_exp(self):
        self.total_exp = 0
        self.last_exp = None
        LOGGER.info("Experience session stats reset")

    def on_info_stat(self, raw_line: str):
        """Callback for parsed info statistics."""
        stat = self._parse_stat(raw_line)
        if stat is None:
            return

        item_name, val, mx_val = stat.name, stat.value, stat.max_value
        if item_name:
            LOGGER.debug(f"TTS Stat detected: {item_name}={val}")

        if item_name == "gold_balance":
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
                if self.last_gold > 0 and val > self.last_gold * 10 and val > 10_000_000: self.last_gold = val
                elif val < self.last_gold * 0.01 and self.last_gold > 10_000_000: self.last_gold = val
                else:
                    delta = val - self.last_gold
                    if delta > 0: self.total_gold += delta
                    elapsed = (time.time() - self.start_time) / 3600.0
                    gph = int(self.total_gold / elapsed) if elapsed > (1/60.0) else 0
                    update_info_stats(gph=gph, total_gained=self.total_gold)
                    self.last_gold = val
                self.pending_gold, self.gold_verify_count = None, 0
        elif item_name == "experience_gain":
            if self.last_exp is None:
                self.last_exp, self.max_exp, self.start_time = val, mx_val, self.start_time or time.time()
                update_info_stats(eph=0, total_exp=0, t2l="-")
                return
            delta = val - self.last_exp
            if delta > 0: self.total_exp += delta
            self.last_exp, self.max_exp = val, mx_val or self.max_exp
            elapsed = (time.time() - self.start_time) / 3600.0
            eph = int(self.total_exp / elapsed) if elapsed > (1/60.0) else 0
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
        if self.hover_active or _BUSY_CHECKER(): return
        info_config = load_info_settings()
        if not info_config.get("check_exp_on_inventory_open", True): return
        if IniConfigLoader().advanced_options.vision_mode_only: return
        
        now = time.time()
        is_init = SessionStats().last_exp is not None
        if (now - self.last_hover_time) < (info_config.get("exp_age_before_refresh", 5) * 60 if is_init else 2.0): return

        def _task():
            try: self.hover_active = True; time.sleep(0.5); _hover_experience_balance(info_config); mouse.move(*Cam().abs_window_to_monitor((0, 0)))
            finally: self.hover_active = False
        self.last_hover_time = now
        threading.Thread(target=_task, daemon=True).start()

TRANSPARENT_KEY = "#ff00ff"
CARD_BG = "#151515"
TEXT = "#ffffff"
ACCENT = "#cfa15b"
LEGION_BLUE = "#56B4E9"
HELLTIDE_RED = "#ff4d4d"
WB_ORANGE = "#e67e22"
WARNING_ORANGE = "#ff9900"
ACTIVE_GREEN = "#34C410"

class BossTimerOverlay(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("D4LF Boss Timer")
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.wm_attributes("-transparentcolor", TRANSPARENT_KEY)
        self.configure(bg=TRANSPARENT_KEY)

        self._gold_initialized = False
        self._exp_initialized = False

        self.settings = load_info_settings()
        self._apply_loaded_settings()
        self._flash_toggle = False
        self._setup_ui()
        self._bind_events()
        self._update_timers()
        # Auto-sync on startup
        self._session_stats = SessionStats()
        self._session_stats.subscribe()
        self._auto_sync()

    def destroy(self):
        """Perform cleanup and unsubscribe from stats on destruction."""
        self._session_stats.unsubscribe()
        super().destroy()

    def _apply_loaded_settings(self):
        self.x, self.y = self.settings["x"], self.settings["y"]
        self.font_size = self.settings["font_size"]
        self.next_boss_name = self.settings["next_boss_name"]
        self.orientation = self.settings["orientation"]
        self.locked = self.settings["locked"]
        
        # Assign all show_ attributes
        for k in self.settings:
            if k.startswith("show_"):
                setattr(self, k, self.settings[k])

        wb_ref_str = self.settings["wb_reference"]
        try:
            self.wb_reference = datetime.datetime.strptime(wb_ref_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            self.wb_reference = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

        # In-memory synced data
        self.synced_wb = None
        self.synced_legion = None
        self.synced_helltide = None

    def _save_settings(self):
        updates = {
            "x": self.winfo_x(),
            "y": self.winfo_y(),
            "font_size": self.font_size,
            "wb_reference": self.wb_reference.strftime("%Y-%m-%d %H:%M:%S"),
            "next_boss_name": self.next_boss_name,
            "orientation": self.orientation,
            "locked": self.locked,
        }
        # Sync show_ attributes
        for k in self.settings:
            if k.startswith("show_"):
                updates[k] = getattr(self, k)
        
        save_info_settings(updates)
        self.settings = load_info_settings()

    def _setup_ui(self):
        self.labels_to_resize = []
        self.frame = tk.Frame(self, bg=CARD_BG, highlightthickness=1, highlightbackground=ACCENT)
        self.frame.pack(padx=5, pady=5)

        self.wb_group = tk.Frame(self.frame, bg=CARD_BG)
        lbl_wb = tk.Label(self.wb_group, text="World Boss:", bg=CARD_BG, fg=WB_ORANGE, font=("Consolas", self.font_size, "bold"))
        lbl_wb.pack(side="left")
        self.labels_to_resize.append(lbl_wb)
        self.wb_timer = tk.Label(self.wb_group, text="--:--:--", bg=CARD_BG, fg=TEXT, font=("Consolas", self.font_size, "bold"))
        self.wb_timer.pack(side="left")
        self.labels_to_resize.append(self.wb_timer)

        self.legion_group = tk.Frame(self.frame, bg=CARD_BG)
        self.lbl_legion = tk.Label(self.legion_group, text="Legion:", bg=CARD_BG, fg=LEGION_BLUE, font=("Consolas", self.font_size, "bold"))
        self.lbl_legion.pack(side="left")
        self.labels_to_resize.append(self.lbl_legion)
        self.legion_timer = tk.Label(self.legion_group, text="--:--:--", bg=CARD_BG, fg=TEXT, font=("Consolas", self.font_size, "bold"))
        self.legion_timer.pack(side="left")
        self.labels_to_resize.append(self.legion_timer)

        self.ht_group = tk.Frame(self.frame, bg=CARD_BG)
        self.lbl_ht = tk.Label(self.ht_group, text="Helltide:", bg=CARD_BG, fg=HELLTIDE_RED, font=("Consolas", self.font_size, "bold"))
        self.lbl_ht.pack(side="left")
        self.labels_to_resize.append(self.lbl_ht)
        self.ht_timer = tk.Label(self.ht_group, text="--:--:--", bg=CARD_BG, fg=TEXT, font=("Consolas", self.font_size, "bold"))
        self.ht_timer.pack(side="left")
        self.labels_to_resize.append(self.ht_timer)

        self.stats_group = tk.Frame(self.frame, bg=CARD_BG)
        self.lbl_gph_title = tk.Label(self.stats_group, text="GPH:", bg=CARD_BG, fg=ACCENT, font=("Consolas", self.font_size, "bold"))
        self.lbl_gph_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_gph_title)
        self.gph_value_label = tk.Label(self.stats_group, text="0", bg=CARD_BG, fg=TEXT, font=("Consolas", self.font_size, "bold"))
        self.gph_value_label.pack(side="left")
        self.labels_to_resize.append(self.gph_value_label)

        self.lbl_total_gained_title = tk.Label(self.stats_group, text="|Gained:", bg=CARD_BG, fg=ACCENT, font=("Consolas", self.font_size, "bold"))
        self.lbl_total_gained_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_total_gained_title)
        self.total_gained_value_label = tk.Label(self.stats_group, text="0", bg=CARD_BG, fg=TEXT, font=("Consolas", self.font_size, "bold"))
        self.total_gained_value_label.pack(side="left")
        self.labels_to_resize.append(self.total_gained_value_label)

        self.exp_group = tk.Frame(self.frame, bg=CARD_BG)
        self.lbl_eph_title = tk.Label(self.exp_group, text="EPH:", bg=CARD_BG, fg=LEGION_BLUE, font=("Consolas", self.font_size, "bold"))
        self.lbl_eph_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_eph_title)
        self.eph_value_label = tk.Label(self.exp_group, text="0", bg=CARD_BG, fg=TEXT, font=("Consolas", self.font_size, "bold"))
        self.eph_value_label.pack(side="left")
        self.labels_to_resize.append(self.eph_value_label)

        self.lbl_total_exp_title = tk.Label(self.exp_group, text="|Exp:", bg=CARD_BG, fg=LEGION_BLUE, font=("Consolas", self.font_size, "bold"))
        self.lbl_total_exp_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_total_exp_title)
        self.total_exp_value_label = tk.Label(self.exp_group, text="0", bg=CARD_BG, fg=TEXT, font=("Consolas", self.font_size, "bold"))
        self.total_exp_value_label.pack(side="left")
        self.labels_to_resize.append(self.total_exp_value_label)

        self.t2l_group = tk.Frame(self.frame, bg=CARD_BG)
        self.lbl_t2l_title = tk.Label(self.t2l_group, text="T2L:", bg=CARD_BG, fg=LEGION_BLUE, font=("Consolas", self.font_size, "bold"))
        self.lbl_t2l_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_t2l_title)
        self.t2l_value_label = tk.Label(self.t2l_group, text="-", bg=CARD_BG, fg=TEXT, font=("Consolas", self.font_size, "bold"))
        self.t2l_value_label.pack(side="left")
        self.labels_to_resize.append(self.t2l_value_label)

        self.lbl_next_scan_title = tk.Label(self.t2l_group, text="|Next Scan:", bg=CARD_BG, fg=LEGION_BLUE, font=("Consolas", self.font_size, "bold"))
        self.lbl_next_scan_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_next_scan_title)
        self.next_scan_value_label = tk.Label(self.t2l_group, text="Ready", bg=CARD_BG, fg=TEXT, font=("Consolas", self.font_size, "bold"))
        self.next_scan_value_label.pack(side="left")
        self.labels_to_resize.append(self.next_scan_value_label)

        self._repack()
        self.geometry(f"+{self.x}+{self.y}")

    def _repack(self):
        """Recalculate component packing based on current settings."""
        LOGGER.debug(f"Repacking overlay. show_gold={self.show_gold}, _gold_initialized={self._gold_initialized}, show_gph={self.show_gph}, show_total_gold={self.show_total_gold}, show_exp={self.show_exp}, _exp_initialized={self._exp_initialized}, show_eph={self.show_eph}, show_total_exp={self.show_total_exp}, show_t2l={self.show_t2l}, show_next_scan={self.show_next_scan}")
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
        if self.show_gold and self._gold_initialized and (self.show_gph or self.show_total_gold):
            self._repack_gold_group()
            self.stats_group.pack(side=side, anchor=anchor, padx=2)
        if self.show_exp and self._exp_initialized:
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
        self._repack()
        self._save_settings()

    def _toggle_visibility(self, key):
        current = getattr(self, key)
        setattr(self, key, not current)
        self._repack()
        self._save_settings()

    def _show_context_menu(self, event):
        """Create and display a right-click context menu."""
        menu = tk.Menu(
            self,
            tearoff=0,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            selectcolor=ACTIVE_GREEN,
        )
        self._menu_vars = []

        def add_config_check(m, label, field):
            var = tk.BooleanVar(master=self, value=self.settings[field])
            self._menu_vars.append(var)
            def _toggle():
                val = not self.settings[field]
                save_info_settings({field: val})
                self.settings[field] = val
            m.add_checkbutton(label=label, variable=var, command=_toggle)

        def add_check(m, label, attr, cmd):
            var = tk.BooleanVar(master=self, value=getattr(self, attr))
            self._menu_vars.append(var)
            m.add_checkbutton(label=label, variable=var, command=cmd)

        add_check(menu, "Show World Boss", "show_wb", lambda: self._toggle_visibility("show_wb"))
        add_check(menu, "Show Legion", "show_legion", lambda: self._toggle_visibility("show_legion"))
        add_check(menu, "Show Helltide", "show_ht", lambda: self._toggle_visibility("show_ht"))

        # Gold Submenu
        gold_menu = tk.Menu(menu, tearoff=0, bg=CARD_BG, fg=TEXT, activebackground=ACCENT, activeforeground=CARD_BG, selectcolor=ACTIVE_GREEN)
        add_check(gold_menu, "Show Gold Stats", "show_gold", lambda: self._toggle_visibility("show_gold"))
        gold_menu.add_separator()
        add_check(gold_menu, "Show Gold Per Hour", "show_gph", lambda: self._toggle_visibility("show_gph"))
        add_check(gold_menu, "Show Total Gold", "show_total_gold", lambda: self._toggle_visibility("show_total_gold"))
        gold_menu.add_separator()
        gold_menu.add_command(label="Reset Gold Stats", command=self._reset_gold_stats)
        menu.add_cascade(label="Show Gold Stats", menu=gold_menu)

        # Exp Submenu
        exp_menu = tk.Menu(menu, tearoff=0, bg=CARD_BG, fg=TEXT, activebackground=ACCENT, activeforeground=CARD_BG, selectcolor=ACTIVE_GREEN)
        add_check(exp_menu, "Show Exp Stats", "show_exp", lambda: self._toggle_visibility("show_exp"))
        exp_menu.add_separator()
        add_check(exp_menu, "Show EXP Per Hour", "show_eph", lambda: self._toggle_visibility("show_eph"))
        add_check(exp_menu, "Show Total EXP", "show_total_exp", lambda: self._toggle_visibility("show_total_exp"))
        add_check(exp_menu, "Show Time to Level", "show_t2l", lambda: self._toggle_visibility("show_t2l"))
        add_check(exp_menu, "Show Next Scan", "show_next_scan", lambda: self._toggle_visibility("show_next_scan"))
        exp_menu.add_separator() # Separator before config options
        add_config_check(exp_menu, "Check EXP on Open", "check_exp_on_inventory_open") # Moved here
        
        exp_menu.add_separator()

        # Submenu for EXP Age selection
        age_menu = tk.Menu(
            exp_menu,
            tearoff=0,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            selectcolor=ACTIVE_GREEN,
        )
        age_var = tk.IntVar(master=self, value=self.settings["exp_age_before_refresh"])
        self._menu_vars.append(age_var)

        for m in [0, 3, 5, 10, 30, 60]:
            age_menu.add_radiobutton(
                label=f"{m}m", variable=age_var, value=m, command=lambda v=m: save_info_settings({"exp_age_before_refresh": v})
            )
        exp_menu.add_cascade(label="EXP Age Before Refresh", menu=age_menu)

        exp_menu.add_command(label="Pick EXP Bar Position", command=self._pick_exp_bar_pos)
        if self.settings["exp_bar_pos"] is not None:
            exp_menu.add_command(label="Reset EXP Bar Position", command=self._reset_exp_bar_pos)

        exp_menu.add_separator()
        exp_menu.add_command(label="Reset Exp Stats", command=self._reset_exp_stats)
        menu.add_cascade(label="Show Exp Stats", menu=exp_menu)

        menu.add_separator()
        menu.add_command(label=f"Orientation: {self.orientation.title()}", command=self._toggle_orientation)
        menu.add_command(label="Increase Size (+)", command=lambda: self._change_size(2))
        menu.add_command(label="Decrease Size (-)", command=lambda: self._change_size(-2))

        menu.add_separator()
        menu.add_command(label="Auto Sync (Helltides.com)", command=self._auto_sync)

        menu.add_separator()
        add_check(menu, "Lock Position", "locked", self._toggle_lock)
        menu.add_command(label="Close Overlay", command=request_close)
        
        menu.post(event.x_root, event.y_root)

    def _reset_gold_stats(self):
        SessionStats().reset_gold()
        self._gold_initialized = False
        self.update_stats(gph=0, total_gained=0)
        self._repack()

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
            text=msg, font=("Consolas", 20, "bold"), fill=ACTIVE_GREEN
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
        self.frame.bind("<Button-1>", self._start_drag)
        self.frame.bind("<B1-Motion>", self._do_drag)
        self.frame.bind("<ButtonRelease-1>", self._stop_drag)
        self.frame.bind("<Button-3>", self._show_context_menu)
        self.bind("<Button-3>", self._show_context_menu)

    def _change_size(self, delta):
        self.font_size = max(8, min(48, self.font_size + delta))
        for lbl in self.labels_to_resize:
            lbl.config(font=("Consolas", self.font_size, "bold"))
        self._save_settings()

    def _toggle_lock(self, event=None):
        self.locked = not self.locked
        self._save_settings()

    def _start_drag(self, event):
        if self.locked: return
        self._drag_data = {"x": event.x, "y": event.y}

    def _do_drag(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    def _stop_drag(self, event):
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
                    now = datetime.datetime.now(datetime.timezone.utc)
                    
                    # Regex for World Bosses: "BossName","world_boss","YYYY-MM-DDTHH:MM:SS.000Z"
                    wb_pattern = r'\"(Ashava|Avarice|Wandering Death)\",\"world_boss\",\"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\"'
                    wb_matches = re.findall(wb_pattern, text)
                    
                    # Regex for Legions: "legion","YYYY-MM-DDTHH:MM:SS.000Z"
                    legion_pattern = r'\"legion\",\"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\"'
                    legion_matches = re.findall(legion_pattern, text)
                    
                    # Regex for Helltides: "YYYY-MM-DDTHH:MM:SS.000Z","helltide"
                    ht_pattern = r'\"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\",\"helltide\"'
                    ht_matches = re.findall(ht_pattern, text)

                    # Process World Bosses
                    best_wb = None
                    for name, dt_str in wb_matches:
                        dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc)
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
                        dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc)
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
                        dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc)
                        if dt <= now:
                            if latest_start is None or dt > latest_start:
                                latest_start = dt
                        elif dt > now:
                            if latest_start is None:
                                latest_start = dt
                    if latest_start:
                        self.synced_helltide = latest_start
                        LOGGER.info(f"Auto-synced Helltide: {latest_start}")

                    if self.winfo_exists():
                        self.after(0, self._update_timers)
        except Exception as e:
            LOGGER.error(f"Failed to auto-sync from helltides.com: {e}")

    def _update_timers(self):
        if not self.winfo_exists():
            return
        now = datetime.datetime.now(datetime.timezone.utc)
        self._flash_toggle = not self._flash_toggle

        def get_flash_color(seconds, base_color):
            if 0 < seconds < 300 and not self._flash_toggle:
                return TEXT
            if 0 < seconds < 300:
                return WARNING_ORANGE
            return base_color

        # --- World Boss ---

        # World Boss
        if self.synced_wb and self.synced_wb[0] > now:
            next_wb = self.synced_wb[0]
            boss_name = self.synced_wb[1]
        else:
            # Fallback to 3.5h interval from reference
            wb_interval = datetime.timedelta(hours=3.5)
            time_since_wb = now - self.wb_reference
            intervals_passed = time_since_wb // wb_interval
            next_wb = self.wb_reference + (intervals_passed + 1) * wb_interval
            if next_wb < now:
                next_wb += wb_interval
            boss_name = self.next_boss_name

        wb_remaining = next_wb - now
        if wb_remaining.total_seconds() < 0:
            self.wb_timer.config(text="ACTIVE")
            self.wb_timer.config(fg=ACTIVE_GREEN) # Active WB is green
        else:
            self.wb_timer.config(text=str(wb_remaining).split('.')[0], fg=get_flash_color(wb_remaining.total_seconds(), ACTIVE_GREEN))
        # --- Legion ---
        # Legion
        if self.synced_legion and self.synced_legion > now:
            legion_remaining = self.synced_legion - now
        else:
            # Fallback to 25m interval
            legion_interval = datetime.timedelta(minutes=25)
            legion_ref = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
            time_since_legion = now - legion_ref
            legion_passed = time_since_legion // legion_interval
            next_legion = legion_ref + (legion_passed + 1) * legion_interval
            legion_remaining = next_legion - now
        self.legion_timer.config(text=str(legion_remaining).split('.')[0], fg=get_flash_color(legion_remaining.total_seconds(), ACTIVE_GREEN))

        # --- Helltide ---
        # Helltide
        # Diablo 4 Helltides cycle every hour: 55 minutes active, 5 minutes break.
        ht_ref = self.synced_helltide or now.replace(minute=0, second=0, microsecond=0)
        diff = (now - ht_ref).total_seconds()

        if diff < 0:
            # Synced reference is in the future
            ht_rem = ht_ref - now
            self.ht_timer.config(text=str(ht_rem).split('.')[0], fg=get_flash_color(ht_rem.total_seconds(), TEXT))
        else:
            # Normalized position in the infinite 1-hour cycle
            cycle_pos = diff % 3600
            if cycle_pos < 3300:
                # Active (0-55 mins)
                rem = datetime.timedelta(seconds=int(3300 - cycle_pos))
                self.ht_timer.config(text=str(rem).split('.')[0], fg=ACTIVE_GREEN)
            else:
                # Break / Warning (55-60 mins)
                rem = datetime.timedelta(seconds=int(3600 - cycle_pos))
                self.ht_timer.config(text=str(rem).split('.')[0], fg=get_flash_color(rem.total_seconds(), WARNING_ORANGE))

        # --- Next Scan Cooldown ---
        with suppress(Exception):
            info_conf = load_info_settings()
            if not info_conf["check_exp_on_inventory_open"]:
                self.next_scan_value_label.config(text="Off")
            elif SessionStats().last_exp is None:
                self.next_scan_value_label.config(text="Ready")
            else:
                remaining = (info_conf["exp_age_before_refresh"] * 60) - (time.time() - InventoryExpTracker().last_hover_time)
                if remaining <= 0:
                    self.next_scan_value_label.config(text="Ready")
                else:
                    m, s = divmod(int(remaining), 60)
                    self.next_scan_value_label.config(text=f"{m}m {s}s" if m > 0 else f"{s}s")

        self.after(1000, self._update_timers)

    def update_stats(self, gph: int | None = None, total_gained: int | None = None, eph: int | None = None, total_exp: int | None = None, t2l: str | None = None):
        """Update the gold and experience statistics display."""
        repack_needed = False
        if gph is not None:
            self.gph_value_label.config(text=f"{gph:,}")
            if not self._gold_initialized:
                self._gold_initialized = True
                repack_needed = True
        if total_gained is not None:
            self.total_gained_value_label.config(text=f"{total_gained:,}")
            if not self._gold_initialized:
                self._gold_initialized = True
                repack_needed = True
        if eph is not None:
            self.eph_value_label.config(text=f"{eph:,}")
            if not self._exp_initialized:
                self._exp_initialized = True
                repack_needed = True
        if total_exp is not None:
            self.total_exp_value_label.config(text=f"{total_exp:,}")
            if not self._exp_initialized:
                self._exp_initialized = True
                repack_needed = True
        if t2l is not None:
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
    # Stop the mainloop first via quit(), then destroy root on the UI thread.
    root.destroy()
    with _OVERLAY_LOCK:
        _OVERLAY_INSTANCE = None

def request_close():
    """Thread-safe request to close the overlay."""
    with _OVERLAY_LOCK:
        if _OVERLAY_INSTANCE and _OVERLAY_INSTANCE.winfo_exists():
            # Schedule the mainloop to exit on the UI thread
            _OVERLAY_INSTANCE.after(0, _OVERLAY_INSTANCE.master.quit)

def update_info_stats(gph: int | None = None, total_gained: int | None = None, eph: int | None = None, total_exp: int | None = None, t2l: str | None = None):
    """Thread-safe update for statistics."""
    with _OVERLAY_LOCK:
        if _OVERLAY_INSTANCE and _OVERLAY_INSTANCE.winfo_exists():
            _OVERLAY_INSTANCE.after(0, lambda: _OVERLAY_INSTANCE.update_stats(gph, total_gained, eph, total_exp, t2l))

def _hover_experience_balance(info_config: dict[str, Any] | None = None):
    if info_config is None: info_config = load_info_settings()
    if info_config["exp_bar_pos"]:
        if len(info_config["exp_bar_pos"]) == 4:
            x1, y1, x2, y2 = info_config["exp_bar_pos"]
            mouse.move(*Cam().window_to_monitor((x1, y1)))
            time.sleep(0.1)
            mouse.move(*Cam().window_to_monitor((x2, y2)))
        else:
            mouse.move(*Cam().window_to_monitor(info_config["exp_bar_pos"]))
    else:
        win_roi = Cam().window_roi
        exp_pos = (int(win_roi["width"] * 0.5), int(win_roi["height"] * 0.965))
        mouse.move(*Cam().window_to_monitor(exp_pos))
    time.sleep(0.5)

def toggle_info_overlay():
    """Toggle the Info Panel overlay (thread-safe with debouncing)."""
    global _LAST_TOGGLE_TIME, _OVERLAY_THREAD
    to_stop = False
    with _OVERLAY_LOCK:
        now = time.time()
        # Debounce to prevent rapid key-repeat triggers
        if now - _LAST_TOGGLE_TIME < 1.5:
            return
        _LAST_TOGGLE_TIME = now

        if _OVERLAY_INSTANCE and _OVERLAY_INSTANCE.winfo_exists():
            to_stop = True
            request_close()
        else:
            LOGGER.info("Opening Info Panel overlay")
            _OVERLAY_THREAD = threading.Thread(target=run_boss_timer_overlay, daemon=True)
            _OVERLAY_THREAD.start()
            # Ensure the thread starts and registers the instance before releasing lock
            time.sleep(0.1)

    if to_stop:
        LOGGER.info("Closing Info Panel overlay")
        if _OVERLAY_THREAD and _OVERLAY_THREAD.is_alive():
            _OVERLAY_THREAD.join(timeout=2.0)
        _OVERLAY_THREAD = None
