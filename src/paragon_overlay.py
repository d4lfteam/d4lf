"""Paragon overlay (tkinter)."""

from __future__ import annotations

import base64
import configparser
import ctypes
import io
import logging
import re
import sys
import threading
import tkinter as tk
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None  # type: ignore[assignment]
from pydantic import ValidationError

from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import ProfileModel
from src.config.ui import ResManager
from src.item.filter import _UniqueKeyLoader

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

LOGGER = logging.getLogger(__name__)

# Global overlay instance + close request. This avoids calling Tk APIs from
# non-Tk threads (the hotkey handler runs in a different thread).
_CURRENT_OVERLAY: ParagonOverlay | None = None
_CLOSE_REQUESTED = threading.Event()
_OVERLAY_LOCK = threading.Lock()

# Theme
TRANSPARENT_KEY = "#ff00ff"
CARD_BG = "#151515"
TEXT = "#ffffff"
MUTED = "#cfcfcf"
GOLD = "#cfa15b"
SELECT_BG = "#1f1f1f"
NODE_GREEN = "#18dd44"
NODE_BLUE = "#2da3ff"

# Font sizes in pt - edit here to adjust all UI text
# All values are multiplied by ui_scale at runtime (DPI-aware)
FS_PANEL_TITLE = 13  # Build/profile title in panel header
FS_MODE_LABEL = 10  # "Full View" / "Compact View" label
FS_BUTTON = 12  # "Builds" and settings button labels
FS_BOARD_CARD = 10  # Board card entries in the left panel list
FS_BUILDS_MENU = 12  # Items in the "Builds" dropdown menu
FS_SETTINGS_ICON = 13  # Icons in the settings popup rows
FS_SETTINGS_LABEL = 10  # Label text in the settings popup rows
FS_ZOOM_BTN = 15  # zoom buttons
FS_HINT = 10  # Hint / move-grid text at bottom of settings

# Panel width in px (base value, DPI-scaled at runtime)
PANEL_W = 370
GRID = 21  # 21x21 nodes
NODES_LEN = GRID * GRID

# ----------------------------
# Windows DPI helpers
# ----------------------------
_TK_BASELINE_SCALING = 96 / 72  # pixels per point (Tk). Baseline to make ui_scale predictable.


def _enable_windows_dpi_awareness() -> None:
    """Best-effort: make the process Per-Monitor DPI aware on Windows.

    Must be called before creating the Tk root window to fully take effect.
    """
    if sys.platform != "win32":
        return

    # Attempt methods in order; stop at first success.
    with suppress(Exception):
        # Windows 10+: Per Monitor v2
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return

    with suppress(Exception):
        # Windows 8.1+: PROCESS_PER_MONITOR_DPI_AWARE = 2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return

    # Vista+: system DPI aware
    with suppress(Exception):
        ctypes.windll.user32.SetProcessDPIAware()


def _win_dpi_for_hwnd(hwnd: int) -> int | None:
    """Return DPI for a window handle (Windows), or None on failure."""
    if sys.platform != "win32":
        return None
    try:
        return int(ctypes.windll.user32.GetDpiForWindow(int(hwnd)))
    except Exception:
        return None


def _dpi_scale_for_widget(w: tk.Misc) -> float:
    """Return scale factor vs 96 DPI for the widget's monitor (best effort)."""
    # Try Windows per-window DPI first.
    dpi = None
    try:
        dpi = _win_dpi_for_hwnd(w.winfo_id())
    except Exception:
        dpi = None

    # Fallback: infer DPI from current Tk scaling (pixels/point * 72 = dpi).
    if dpi is None:
        try:
            s = float(w.tk.call("tk", "scaling"))
            dpi = round(s * 72)
        except Exception:
            dpi = 96

    try:
        return float(dpi) / 96.0
    except Exception:
        return 1.0


def _params_ini_path() -> Path:
    user_dir = Path.home() / ".d4lf"
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "params.ini"


def _load_overlay_settings() -> dict[str, Any]:
    ini = _params_ini_path()
    if not ini.exists():
        ini.write_text("", encoding="utf-8")

    p = configparser.ConfigParser()
    p.read(ini, encoding="utf-8")
    sec = p["paragon_overlay"] if p.has_section("paragon_overlay") else {}

    def _get_int(k: str) -> int | None:
        v = sec.get(k)
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        try:
            return int(s)
        except Exception:
            return None

    def _get_bool(k: str) -> bool | None:
        v = sec.get(k)
        if v is None:
            return None
        s = str(v).strip().lower()
        if s in ("true", "1", "yes"):
            return True
        if s in ("false", "0", "no"):
            return False
        return None

    def _get_str(k: str) -> str | None:
        v = sec.get(k)
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    return {
        "x": _get_int("x"),
        "y": _get_int("y"),
        "cell_size": _get_int("cell_size"),
        "profile": _get_str("profile"),
        "build_idx": _get_int("build_idx"),
        "board_idx": _get_int("board_idx"),
        "grid_x": _get_int("grid_x"),
        "grid_y": _get_int("grid_y"),
        # Collapsed mode settings
        "is_collapsed": _get_bool("is_collapsed"),
        "cell_size_collapsed": _get_int("cell_size_collapsed"),
        "grid_x_collapsed": _get_int("grid_x_collapsed"),
        "grid_y_collapsed": _get_int("grid_y_collapsed"),
        # Grid lock
        "grid_locked": _get_bool("grid_locked"),
    }


def _save_overlay_settings(values: dict[str, Any]) -> None:
    ini = _params_ini_path()
    if not ini.exists():
        ini.write_text("", encoding="utf-8")

    p = configparser.ConfigParser()
    p.read(ini, encoding="utf-8")
    if not p.has_section("paragon_overlay"):
        p.add_section("paragon_overlay")

    sec = p["paragon_overlay"]
    for k, v in values.items():
        if v is None:
            continue
        sec[str(k)] = str(v)

    with ini.open("w", encoding="utf-8") as f:
        p.write(f)


def _clamp_int(v: int | None, lo: int, hi: int, default: int) -> int:
    if v is None:
        return default
    try:
        return max(lo, min(hi, int(v)))
    except Exception:
        return default


# ----------------------------
# Data loading / normalization
# ----------------------------


def _iter_entries(data: Any) -> Iterable[dict[str, Any]]:
    if isinstance(data, dict):
        yield data
        return
    if isinstance(data, list):
        for it in data:
            if isinstance(it, dict):
                yield it


def _normalize_steps(raw_list: Any) -> list[list[dict[str, Any]]]:
    if not isinstance(raw_list, list) or not raw_list:
        return []
    if isinstance(raw_list[0], list):
        return [step for step in raw_list if isinstance(step, list) and step]
    return [raw_list]


def _iter_paragon_payloads(paragon: object) -> list[dict[str, Any]]:
    if isinstance(paragon, dict):
        return [paragon]
    if isinstance(paragon, list):
        return [x for x in paragon if isinstance(x, dict)]
    return []


def _load_profile_model(profile_path: Path, profile_name: str) -> ProfileModel | None:
    try:
        with profile_path.open(encoding="utf-8") as f:
            cfg = yaml.load(stream=f, Loader=_UniqueKeyLoader)
    except Exception:
        LOGGER.debug("Failed reading YAML: %s", profile_path, exc_info=True)
        return None

    if cfg is None:
        return None
    if not isinstance(cfg, dict):
        return None

    try:
        return ProfileModel(name=profile_name, **cfg)
    except ValidationError:
        LOGGER.debug("Profile validation failed for %s", profile_path, exc_info=True)
        return None


def load_builds_from_path(preset_path: str | None = None) -> list[dict[str, Any]]:
    """Load Paragon builds for the overlay.

    Primary source is the currently loaded profile list from the main config (same as Filter.load_files).
    If no profiles are configured, this falls back to scanning the provided directory for *.yaml/*.yml.
    """
    config = IniConfigLoader()
    profiles_dir = config.user_dir / "profiles"
    profile_names = [p.strip() for p in config.general.profiles if p.strip()]

    candidates: list[tuple[str, Path]] = []

    if profile_names:
        for name in profile_names:
            path_yaml = profiles_dir / f"{name}.yaml"
            path_yml = profiles_dir / f"{name}.yml"
            if path_yaml.is_file():
                candidates.append((name, path_yaml))
            elif path_yml.is_file():
                candidates.append((name, path_yml))
            else:
                # Keep behavior consistent with filter.py: log and continue
                LOGGER.debug("Could not load profile %s. Checked: %s", name, path_yaml)
    else:
        # Fallback: scan provided dir (or default profiles dir)
        scan_dir = Path(preset_path) if preset_path else profiles_dir
        if scan_dir.is_file():
            scan_dir = scan_dir.parent
        candidates.extend([
            (fp.stem, fp) for fp in sorted(scan_dir.glob("*.ya*"), key=lambda x: x.stat().st_mtime, reverse=True)
        ])

    builds: list[dict[str, Any]] = []
    for prof_name, prof_path in candidates:
        model = _load_profile_model(prof_path, prof_name)
        if model is None or not model.Paragon:
            continue
        for payload in _iter_paragon_payloads(model.Paragon):
            builds.extend(_builds_from_paragon_entry(payload, name_tag=None, profile=prof_name))

    return builds


def _builds_from_paragon_entry(
    entry: dict[str, Any], *, name_tag: str | None, profile: str | None
) -> list[dict[str, Any]]:
    base_name = entry.get("Name") or entry.get("name") or "Unknown Build"
    steps = _normalize_steps(entry.get("ParagonBoardsList", []))
    if not steps:
        return []

    builds: list[dict[str, Any]] = []
    for idx in range(len(steps) - 1, -1, -1):
        boards = steps[idx]
        step_name = base_name
        if len(steps) > 1:
            step_name = f"{base_name} - Step {idx + 1}"
        if name_tag:
            step_name = f"{step_name} [{name_tag}]"
        builds.append({"name": step_name, "boards": boards, "profile": profile})

    return builds


def parse_rotation(rot_str: str) -> int:
    m = re.search(r"(\d+)", rot_str or "")
    deg = int(m.group(1)) if m else 0
    deg = deg % 360
    return deg if deg in (0, 90, 180, 270) else 0


def nodes_to_grid(nodes_441: list[int] | list[bool]) -> list[list[bool]]:
    return [[bool(nodes_441[y * GRID + x]) for x in range(GRID)] for y in range(GRID)]


def rotate_grid(grid: list[list[bool]], deg: int) -> list[list[bool]]:
    if deg == 90:
        return [list(reversed(col)) for col in zip(*grid, strict=True)]
    if deg == 180:
        return [list(reversed(r)) for r in reversed(grid)]
    if deg == 270:
        return [list(col) for col in reversed(list(zip(*grid, strict=True)))]
    return grid


# ----------------------------
# Overlay UI
# ----------------------------


@dataclass(slots=True)
class OverlayConfig:
    # Full View settings
    cell_size: int = 24
    grid_x_default: int = PANEL_W + 24  # default grid offset: panel width + gap
    grid_y_default: int = 24

    # Collapsed View settings
    cell_size_collapsed: int = 16
    grid_x_collapsed_default: int = 600
    grid_y_collapsed_default: int = 300

    ui_scale: float = 1.0  # Auto-DPI baseline (scaled at runtime)
    panel_w: int = PANEL_W
    poll_ms: int = 500
    window_alpha: float = 0.86

    # State
    is_collapsed: bool = False
    grid_locked: bool = False


class ParagonOverlay(tk.Toplevel):
    """Tkinter paragon overlay window."""

    def __init__(
        self,
        parent: tk.Misc,
        builds: list[dict[str, Any]],
        *,
        cfg: OverlayConfig | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)

        self._settings = _load_overlay_settings()
        self._cfg = cfg or OverlayConfig()
        self._apply_dpi_scaling()

        # Load cell_size for Full View
        saved_cell = self._settings.get("cell_size")
        if isinstance(saved_cell, int):
            self._cfg.cell_size = _clamp_int(saved_cell, 10, 80, self._cfg.cell_size)

        # Load cell_size for Collapsed View
        saved_cell_c = self._settings.get("cell_size_collapsed")
        if isinstance(saved_cell_c, int):
            self._cfg.cell_size_collapsed = _clamp_int(saved_cell_c, 8, 50, self._cfg.cell_size_collapsed)

        # Load collapsed state
        saved_collapsed = self._settings.get("is_collapsed")
        if isinstance(saved_collapsed, bool):
            self._cfg.is_collapsed = saved_collapsed

        # Load grid locked state
        saved_locked = self._settings.get("grid_locked")
        if isinstance(saved_locked, bool):
            self._cfg.grid_locked = saved_locked
        self._on_close = on_close
        self._cam = Cam()
        self._res = ResManager()

        self.builds = list(builds)
        saved_profile = self._settings.get("profile")
        saved_idx = self._settings.get("build_idx")
        idx: int | None = None

        if isinstance(saved_idx, int) and 0 <= saved_idx < len(self.builds):
            idx = saved_idx
            if saved_profile and self.builds[idx].get("profile") != saved_profile:
                idx = None

        if idx is None and saved_profile:
            for i, b in enumerate(self.builds):
                if b.get("profile") == saved_profile:
                    idx = i
                    break

        if idx is None:
            idx = _clamp_int(saved_idx, 0, max(0, len(self.builds) - 1), 0)

        self.current_build_idx = idx
        self.boards = self.builds[self.current_build_idx]["boards"] if self.builds else []
        self.selected_board_idx = _clamp_int(self._settings.get("board_idx"), 0, max(0, len(self.boards) - 1), 0)

        # Grid positions for BOTH modes - Full View
        self.grid_x = self._settings.get("grid_x")
        self.grid_y = self._settings.get("grid_y")
        if not isinstance(self.grid_x, int):
            self.grid_x = self._cfg.panel_w + 24
        if not isinstance(self.grid_y, int):
            self.grid_y = 24

        # Grid positions for Collapsed View
        self.grid_x_collapsed = self._settings.get("grid_x_collapsed")
        self.grid_y_collapsed = self._settings.get("grid_y_collapsed")
        if not isinstance(self.grid_x_collapsed, int):
            self.grid_x_collapsed = self._cfg.grid_x_collapsed_default
        if not isinstance(self.grid_y_collapsed, int):
            self.grid_y_collapsed = self._cfg.grid_y_collapsed_default

        self._last_roi: tuple[int, int, int, int] | None = None
        self._last_res: tuple[int, int] | None = None
        self._dragging_grid = False
        self._dragging_window = False
        self._border_rect: tuple[int, int, int, int] | None = None
        self._border_grab = 12

        self.title("D4LF Paragon Overlay")
        self.attributes("-topmost", True)
        with suppress(tk.TclError):
            self.attributes("-alpha", float(self._cfg.window_alpha))
        self.configure(bg=TRANSPARENT_KEY)
        with suppress(tk.TclError):
            self.overrideredirect(True)
        with suppress(tk.TclError):
            self.wm_attributes("-transparentcolor", TRANSPARENT_KEY)

        self.protocol("WM_DELETE_WINDOW", self.close)

        self._build_ui()
        self._bind_events()
        self._apply_geometry()
        self._refresh_lists()
        self.redraw()
        # Warm up settings popup assets (lock icons) to avoid first-open lag
        # Warm up settings popup assets (lock icons) to avoid first-open lag.
        # Delay slightly so the window can paint first.
        self._warmup_after_id = self.after(600, self._warmup_settings_assets)

        self.after(self._cfg.poll_ms, self._poll_window_state)
        self.after(50, self._poll_close_request)

    def _apply_dpi_scaling(self) -> None:
        """Apply DPI-based scaling to fonts and pixel-based layout.

        Strategy:
        - Force Tk's internal `tk scaling` to a 96-DPI baseline so our manual
          `ui_scale` multiplier is predictable across systems.
        - Compute `ui_scale` from the monitor DPI (vs 96).
        - Scale panel width and default cell size (unless user saved a cell size).
        """
        # Baseline Tk scaling (pixels per point). If this fails, we still keep running.
        with suppress(Exception):
            self.tk.call("tk", "scaling", _TK_BASELINE_SCALING)

        scale = _dpi_scale_for_widget(self)

        # If callers provided cfg.ui_scale as an extra multiplier, apply it.
        # (Default is 1.0; values like 1.1 can slightly enlarge the UI.)
        with suppress(Exception):
            extra = float(self._cfg.ui_scale or 1.0)
            if extra > 0:
                scale *= extra

        eff = max(0.75, min(4.0, float(scale)))
        self._cfg.ui_scale = eff

        # Scale the left panel width so long board names fit better.
        with suppress(Exception):
            base_w = float(self._cfg.panel_w)
            self._cfg.panel_w = round(base_w * eff)

        # If there is no saved cell_size, scale the default cell size too.
        if not isinstance(self._settings.get("cell_size"), int):
            with suppress(Exception):
                base_cell = float(self._cfg.cell_size)
                self._cfg.cell_size = round(base_cell * eff)

        if not isinstance(self._settings.get("cell_size_collapsed"), int):
            with suppress(Exception):
                base_cell_c = float(self._cfg.cell_size_collapsed)
                self._cfg.cell_size_collapsed = round(base_cell_c * eff)

    # -------- UI layout --------

    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg=TRANSPARENT_KEY)
        outer.pack(fill="both", expand=True)

        # Full-screen canvas (grid)
        self.canvas = tk.Canvas(outer, highlightthickness=0, bg=TRANSPARENT_KEY)
        self.canvas.pack(fill="both", expand=True)

        # Left UI container (transparent; cards only)
        self.left = tk.Frame(outer, bg=TRANSPARENT_KEY)
        self.left.place(x=0, y=0, width=self._cfg.panel_w, relheight=1.0)

        # ========== TITLE CARD (Titel + Mode + Dropdown) ==========
        self.card_title = tk.Frame(self.left, bg=CARD_BG)
        self.card_title.pack(
            fill="x",
            padx=int(10 * self._cfg.ui_scale),
            pady=(int(10 * self._cfg.ui_scale), int(8 * self._cfg.ui_scale)),
        )

        # Title Row
        title_row = tk.Frame(self.card_title, bg=CARD_BG)
        title_row.pack(
            fill="both", expand=True, padx=int(12 * self._cfg.ui_scale), pady=(0, int(4 * self._cfg.ui_scale))
        )

        self.lbl_title = tk.Label(
            title_row,
            text="",
            fg=TEXT,
            bg=CARD_BG,
            font=("Segoe UI", int(FS_PANEL_TITLE * self._cfg.ui_scale), "bold"),
            anchor="w",
            wraplength=max(200, self._cfg.panel_w - 40),
            justify="left",
        )
        self.lbl_title.pack(side="left", fill="x", expand=True)

        # Mode Label
        mode_label_frame = tk.Frame(self.card_title, bg=CARD_BG)
        mode_label_frame.pack(fill="x", padx=int(12 * self._cfg.ui_scale))

        mode_text = "Compact View" if self._cfg.is_collapsed else "Full View"
        self.lbl_mode = tk.Label(
            mode_label_frame,
            text=mode_text,
            fg=MUTED,
            bg=CARD_BG,
            font=("Segoe UI", int(FS_MODE_LABEL * self._cfg.ui_scale)),
            anchor="w",
        )
        self.lbl_mode.pack(side="left")

        # View switch button (placed next to the mode label).
        self.btn_view_switch = tk.Button(
            mode_label_frame,
            text=self._get_view_switch_symbol(),
            command=self._toggle_collapsed_mode,
            padx=int(8 * self._cfg.ui_scale),
            pady=int(2 * self._cfg.ui_scale),
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=GOLD,
            bd=0,
            highlightthickness=0,
            font=("Segoe UI", int(FS_BUTTON * self._cfg.ui_scale), "bold"),
            takefocus=0,
        )
        self.btn_view_switch.pack(side="left", padx=(int(8 * self._cfg.ui_scale), 0))

        # ========== BUTTONS CARD (Settings + Builds) ==========
        self.card_buttons = tk.Frame(self.left, bg=CARD_BG)
        self.card_buttons.pack(fill="x", padx=int(10 * self._cfg.ui_scale), pady=(0, int(8 * self._cfg.ui_scale)))

        buttons_container = tk.Frame(self.card_buttons, bg=CARD_BG)
        buttons_container.pack(
            expand=True, fill="both", padx=int(12 * self._cfg.ui_scale), pady=int(8 * self._cfg.ui_scale)
        )

        self.btn_settings = tk.Button(
            buttons_container,
            text="ParagonOverlay⚙ ▼",
            command=self._show_settings_dropdown,
            padx=int(10 * self._cfg.ui_scale),
            pady=int(6 * self._cfg.ui_scale),
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=GOLD,
            bd=0,
            highlightthickness=0,
            font=("Segoe UI", int(FS_BUTTON * self._cfg.ui_scale), "bold"),
        )
        self.btn_settings.pack(side="left", padx=int(4 * self._cfg.ui_scale))

        self.btn_build_menu = tk.Button(
            buttons_container,
            text="Builds ▼",
            command=self._show_build_menu,
            padx=int(12 * self._cfg.ui_scale),
            pady=int(6 * self._cfg.ui_scale),
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=GOLD,
            bd=0,
            highlightthickness=0,
            font=("Segoe UI", int(FS_BUTTON * self._cfg.ui_scale), "bold"),
        )
        self.btn_build_menu.pack(side="right", padx=int(5 * self._cfg.ui_scale))

        # ========== SCROLLABLE BOARD CARDS ==========
        self.boards_canvas = tk.Canvas(self.left, bg=TRANSPARENT_KEY, highlightthickness=0)
        self.boards_canvas.pack(
            fill="both", expand=True, padx=int(10 * self._cfg.ui_scale), pady=(0, int(12 * self._cfg.ui_scale))
        )

        self.board_container = tk.Frame(self.boards_canvas, bg=TRANSPARENT_KEY)
        self._boards_window_id = self.boards_canvas.create_window((0, 0), window=self.board_container, anchor="nw")

        def _on_container_configure(_: tk.Event) -> None:
            self.boards_canvas.configure(scrollregion=self.boards_canvas.bbox("all"))

        def _on_canvas_configure(e: tk.Event) -> None:
            self.boards_canvas.itemconfigure(self._boards_window_id, width=int(e.width))

        self.board_container.bind("<Configure>", _on_container_configure)
        self.boards_canvas.bind("<Configure>", _on_canvas_configure)

        def _on_container_configure(_: tk.Event) -> None:
            self.boards_canvas.configure(scrollregion=self.boards_canvas.bbox("all"))

        def _on_canvas_configure(e: tk.Event) -> None:
            # Keep cards full width of the visible canvas
            self.boards_canvas.itemconfigure(self._boards_window_id, width=int(e.width))

        self.board_container.bind("<Configure>", _on_container_configure)
        self.boards_canvas.bind("<Configure>", _on_canvas_configure)

    def _bind_events(self) -> None:
        self.boards_canvas.bind("<MouseWheel>", self._on_boards_mousewheel)
        self.boards_canvas.bind("<Button-4>", self._on_boards_mousewheel)
        self.boards_canvas.bind("<Button-5>", self._on_boards_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self._on_grid_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_grid_drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_grid_drag_end)
        for w in (self.card_title, self.lbl_title):
            w.bind("<ButtonPress-1>", self._on_window_drag_start)
            w.bind("<B1-Motion>", self._on_window_drag_move)
            w.bind("<ButtonRelease-1>", self._on_window_drag_end)

    def _poll_close_request(self) -> None:
        if _CLOSE_REQUESTED.is_set():
            _CLOSE_REQUESTED.clear()
            self.close()
            return

        with suppress(Exception):
            if self.winfo_exists():
                self.after(50, self._poll_close_request)

    # -------- polling for ROI/resolution changes --------

    def _poll_window_state(self) -> None:
        try:
            roi = self._get_cam_roi()
            res = self._get_resolution()
            if roi != self._last_roi or res != self._last_res:
                self._last_roi = roi
                self._last_res = res
                self._apply_geometry()
                self.redraw()
        finally:
            self.after(self._cfg.poll_ms, self._poll_window_state)

    # -------- build selection --------

    def _select_build(self, idx: int) -> None:
        if not self.builds:
            return
        idx = _clamp_int(idx, 0, max(0, len(self.builds) - 1), 0)
        self.current_build_idx = idx
        self.boards = self.builds[idx]["boards"] if self.builds else []
        self.selected_board_idx = 0
        self._refresh_lists()
        self.redraw()
        self._persist_state()

    def _toggle_grid_lock(self) -> None:
        """Toggle grid lock (prevent zoom/move)."""
        self._cfg.grid_locked = not self._cfg.grid_locked

        self._persist_state()
        LOGGER.info(f"Grid {'locked' if self._cfg.grid_locked else 'unlocked'}")

    def _is_colorblind_enabled(self) -> bool:
        """Return True if the global (app) colorblind mode is enabled.

        The overlay does not keep its own colorblind toggle anymore; it follows the main setting
        from the Settings GUI (general.colorblind_mode).
        """
        try:
            cfg = IniConfigLoader()
            return bool(getattr(cfg.general, "colorblind_mode", False))
        except Exception:
            return False

    def _reload_profiles(self) -> None:
        """Reload profiles from YAML files."""
        try:
            new_builds = load_builds_from_path()
            if not new_builds:
                LOGGER.warning("No builds found after reload")
                return

            self.builds = new_builds

            # Try to keep current selection
            if 0 <= self.current_build_idx < len(self.builds):
                self.boards = self.builds[self.current_build_idx]["boards"]
            else:
                self.current_build_idx = 0
                self.boards = self.builds[0]["boards"] if self.builds else []

            self.selected_board_idx = min(self.selected_board_idx, max(0, len(self.boards) - 1))

            self._refresh_lists()
            self.redraw()
            LOGGER.info("Profiles reloaded successfully")

        except Exception:
            LOGGER.exception("Failed to reload profiles")

    def _show_build_menu(self) -> None:
        if not self.builds:
            return

        menu_font = ("Segoe UI", int(FS_BUILDS_MENU * self._cfg.ui_scale))
        m = tk.Menu(
            self,
            tearoff=0,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=SELECT_BG,
            activeforeground=GOLD,
            bd=0,
            font=menu_font,
        )
        groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}

        for i, b in enumerate(self.builds):
            prof = str(b.get("profile") or "Ungrouped")
            groups.setdefault(prof, []).append((i, b))

        def _add_item(menu: tk.Menu, i: int, b: dict[str, Any]) -> None:
            name = str(b.get("name") or "Unknown Build")
            menu.add_command(label=name, command=lambda idx=i: self._select_build(idx))

        if len(groups) > 1:
            for prof in sorted(groups):
                sm = tk.Menu(
                    self,
                    tearoff=0,
                    bg=CARD_BG,
                    fg=TEXT,
                    activebackground=SELECT_BG,
                    activeforeground=GOLD,
                    bd=0,
                    font=menu_font,
                )
                for i, b in groups[prof]:
                    _add_item(sm, i, b)
                m.add_cascade(label=prof, menu=sm)
        else:
            for i, b in enumerate(self.builds):
                _add_item(m, i, b)

        self.btn_build_menu.config(fg=GOLD)

        def _poll_menu_closed() -> None:
            with suppress(Exception):
                if m.winfo_exists() and m.winfo_viewable():
                    self.after(80, _poll_menu_closed)
                    return
            with suppress(Exception):
                self.btn_build_menu.config(fg=TEXT)

        try:
            x = self.btn_build_menu.winfo_rootx()
            y = self.btn_build_menu.winfo_rooty() + self.btn_build_menu.winfo_height()
            m.tk_popup(x, y)
        finally:
            with suppress(Exception):
                m.grab_release()
            self.after(80, _poll_menu_closed)

    def _hide_cards(self) -> None:
        with suppress(Exception):
            self.boards_canvas.pack_forget()

    def _show_cards(self) -> None:
        with suppress(Exception):
            self.boards_canvas.pack(
                fill="both", expand=True, padx=int(10 * self._cfg.ui_scale), pady=(0, int(12 * self._cfg.ui_scale))
            )

    def _show_settings_dropdown(self) -> None:
        existing = getattr(self, "_settings_popup", None)
        if existing is not None:
            # If the popup was already destroyed (stale reference), clear it and continue opening.
            if not bool(getattr(existing, "winfo_exists", lambda: 0)()):
                self._settings_popup = None
                existing = None
            else:
                with suppress(Exception):
                    existing.destroy()
                self._settings_popup = None
                self._show_cards()
                with suppress(Exception):
                    self.btn_settings.config(fg=TEXT)  # back to white when closing
                return

        # Cancel any pending warmup so it can't race with popup creation.
        warmup_id = getattr(self, "_warmup_after_id", None)
        if warmup_id:
            with suppress(Exception):
                self.after_cancel(warmup_id)
            self._warmup_after_id = None

        # Ensure lock icon cache exists (usually warmed up during init).
        if not hasattr(self, "_lock_img_cache"):
            self._warmup_settings_assets()

        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=CARD_BG)
        self._settings_popup = popup

        def _on_popup_destroy(event: tk.Event) -> None:
            if event.widget is popup:
                self._settings_popup = None
                self._show_cards()
                with suppress(Exception):
                    self.btn_settings.config(fg=TEXT)

        popup.bind("<Destroy>", _on_popup_destroy, add="+")
        self._hide_cards()
        self._build_settings_popup(popup)
        popup.update_idletasks()
        pw = max(220, popup.winfo_reqwidth())
        ph = popup.winfo_reqheight()
        bx = self.btn_settings.winfo_rootx()
        by = self.btn_settings.winfo_rooty() + self.btn_settings.winfo_height() + 4
        if by + ph > self.winfo_screenheight():
            by = self.btn_settings.winfo_rooty() - ph - 4
        popup.geometry(f"{pw}x{ph}+{bx}+{by}")
        with suppress(Exception):
            self.btn_settings.config(fg=GOLD)  # golden when opened

    def _build_settings_popup(self, popup: tk.Toplevel) -> None:
        scale = self._cfg.ui_scale

        container = tk.Frame(popup, bg=CARD_BG, padx=int(14 * scale), pady=int(10 * scale))
        container.pack(fill="both", expand=True)

        lock_imgs: dict[bool, tk.PhotoImage | None] = getattr(self, "_lock_img_cache", {})

        def _row(
            *,
            icon_text: str | None,
            icon_img: tk.PhotoImage | None,
            label_text: str,
            is_active: bool,
            command: Callable[[], None],
        ) -> tuple[tk.Button, tk.Label]:
            fg = GOLD if is_active else TEXT
            row = tk.Frame(container, bg=CARD_BG)
            row.pack(fill="x", pady=int(3 * scale))

            if icon_img is not None:
                btn = tk.Button(
                    row,
                    image=icon_img,
                    command=command,
                    bg=CARD_BG,
                    activebackground=SELECT_BG,
                    bd=0,
                    highlightthickness=0,
                    padx=int(6 * scale),
                    pady=int(4 * scale),
                )
                # Keep an explicit reference to avoid image GC.
                btn.image = icon_img  # type: ignore[attr-defined]
                btn.pack(side="left")
            else:
                btn = tk.Button(
                    row,
                    text=icon_text or "",
                    command=command,
                    bg=CARD_BG,
                    fg=fg,
                    activebackground=SELECT_BG,
                    activeforeground=GOLD,
                    bd=0,
                    highlightthickness=0,
                    font=("Segoe UI", int(FS_SETTINGS_ICON * scale), "bold"),
                    padx=int(6 * scale),
                    pady=int(4 * scale),
                )
                btn.pack(side="left")

            lbl = tk.Label(
                row, text=label_text, fg=fg, bg=CARD_BG, font=("Segoe UI", int(FS_SETTINGS_LABEL * scale)), anchor="w"
            )
            lbl.pack(side="left", padx=(int(8 * scale), int(24 * scale)))
            return btn, lbl

        # ----- dynamic rows -----

        # lock/unlock: prefer cached images, fall back to emoji text
        locked_now = self._cfg.grid_locked
        lock_img_now = lock_imgs.get(locked_now)
        lock_text_now = "🔒" if locked_now else "🔓"
        btn_lock, lbl_lock = _row(
            icon_text=lock_text_now,
            icon_img=lock_img_now,
            label_text="Grid locked" if locked_now else "Grid unlocked",
            is_active=locked_now,
            command=lambda: (_toggle_grid_lock(), _refresh()),
        )

        btn_reload, lbl_reload = _row(
            icon_text="↻", icon_img=None, label_text="Reload profiles", is_active=False, command=self._reload_profiles
        )

        tk.Frame(container, bg=MUTED, height=1).pack(fill="x", pady=int(6 * scale))

        # ----- zoom row -----

        zoom_row = tk.Frame(container, bg=CARD_BG)
        zoom_row.pack(fill="x", pady=int(3 * scale))

        btn_zoom_minus = tk.Button(
            zoom_row,
            text="−",
            command=lambda: (_on_zoom(-1), _refresh()),
            bg=CARD_BG,
            fg=TEXT,
            activebackground=SELECT_BG,
            activeforeground=GOLD,
            bd=0,
            highlightthickness=0,
            font=("Segoe UI", int(FS_ZOOM_BTN * scale), "bold"),
            padx=int(8 * scale),
            pady=int(2 * scale),
        )
        btn_zoom_minus.pack(side="left")

        lbl_cell = tk.Label(
            zoom_row,
            text="",
            fg=TEXT,
            bg=CARD_BG,
            font=("Segoe UI", int(FS_SETTINGS_LABEL * scale), "bold"),
            width=5,
            anchor="center",
        )
        lbl_cell.pack(side="left")

        btn_zoom_plus = tk.Button(
            zoom_row,
            text="+",
            command=lambda: (_on_zoom(+1), _refresh()),
            bg=CARD_BG,
            fg=TEXT,
            activebackground=SELECT_BG,
            activeforeground=GOLD,
            bd=0,
            highlightthickness=0,
            font=("Segoe UI", int(FS_ZOOM_BTN * scale), "bold"),
            padx=int(8 * scale),
            pady=int(2 * scale),
        )
        btn_zoom_plus.pack(side="left")

        tk.Label(
            zoom_row,
            text="Grid Zoom",
            fg=MUTED,
            bg=CARD_BG,
            font=("Segoe UI", int(FS_SETTINGS_LABEL * scale)),
            anchor="w",
        ).pack(side="left", padx=(int(8 * scale), 0))

        tk.Frame(container, bg=MUTED, height=1).pack(fill="x", pady=int(4 * scale))

        # ----- D-Pad -----

        bc = {
            "bg": CARD_BG,
            "fg": TEXT,
            "activebackground": SELECT_BG,
            "activeforeground": GOLD,
            "bd": 1,
            "relief": "flat",
            "highlightthickness": 0,
            "font": ("Segoe UI", int(FS_SETTINGS_ICON * scale), "bold"),
            "width": 2,
            "pady": int(2 * scale),
        }

        dpad_outer = tk.Frame(container, bg=CARD_BG)
        dpad_outer.pack(anchor="w", pady=(int(2 * scale), int(2 * scale)))

        dpad_col = tk.Frame(dpad_outer, bg=CARD_BG)
        dpad_col.pack(side="left")

        sp = int(30 * scale)

        r0 = tk.Frame(dpad_col, bg=CARD_BG)
        r0.pack()
        tk.Frame(r0, bg=CARD_BG, width=sp, height=1).pack(side="left")
        btn_up = tk.Button(r0, text="↑", command=lambda: (_move_grid(0, -1), _refresh()), **bc)
        btn_up.pack(side="left", padx=1, pady=1)
        tk.Frame(r0, bg=CARD_BG, width=sp, height=1).pack(side="left")

        r1 = tk.Frame(dpad_col, bg=CARD_BG)
        r1.pack()
        btn_left = tk.Button(r1, text="←", command=lambda: (_move_grid(-1, 0), _refresh()), **bc)
        btn_left.pack(side="left", padx=1, pady=1)
        tk.Frame(r1, bg=CARD_BG, width=sp, height=1).pack(side="left")
        btn_right = tk.Button(r1, text="→", command=lambda: (_move_grid(1, 0), _refresh()), **bc)
        btn_right.pack(side="left", padx=1, pady=1)

        r2 = tk.Frame(dpad_col, bg=CARD_BG)
        r2.pack()
        tk.Frame(r2, bg=CARD_BG, width=sp, height=1).pack(side="left")
        btn_down = tk.Button(r2, text="↓", command=lambda: (_move_grid(0, 1), _refresh()), **bc)
        btn_down.pack(side="left", padx=1, pady=1)
        tk.Frame(r2, bg=CARD_BG, width=sp, height=1).pack(side="left")

        tk.Label(
            dpad_outer,
            text="Move\nGrid",
            fg=MUTED,
            bg=CARD_BG,
            font=("Segoe UI", int(FS_HINT * scale)),
            anchor="w",
            justify="left",
        ).pack(side="left", padx=(int(8 * scale), 0))

        tk.Frame(container, bg=MUTED, height=1).pack(fill="x", pady=int(6 * scale))

        hint = (
            "• Drag golden frame to move grid\n"
            "• D-Pad ↑ ↓ ← → moves grid per click\n"
            "• Use − + buttons to zoom\n"
            "• Use 🔓 to lock/unlock grid"
        )
        tk.Label(
            container,
            text=hint,
            fg=MUTED,
            bg=CARD_BG,
            font=("Segoe UI", int(FS_HINT * scale)),
            anchor="w",
            justify="left",
            padx=int(4 * scale),
            pady=int(6 * scale),
        ).pack(fill="x")

        # ----- actions + refresh -----

        def _toggle_grid_lock() -> None:
            self._toggle_grid_lock()

        def _on_zoom(delta: int) -> None:
            self._zoom_grid(delta)

        def _move_grid(dx: int, dy: int) -> None:
            self._move_grid(dx, dy)

        def _refresh() -> None:
            is_collapsed = self._cfg.is_collapsed

            # Lock row
            locked = self._cfg.grid_locked
            fg_lock = GOLD if locked else TEXT
            lock_img = lock_imgs.get(locked)
            if lock_img is not None:
                btn_lock.configure(image=lock_img)
                btn_lock.image = lock_img  # type: ignore[attr-defined]
            else:
                btn_lock.configure(text="🔒" if locked else "🔓", fg=fg_lock)
            lbl_lock.configure(text="Grid locked" if locked else "Grid unlocked", fg=fg_lock)

            # Disable/enable controls when locked
            state = tk.DISABLED if locked else tk.NORMAL
            fg_controls = MUTED if locked else TEXT

            for w in (btn_zoom_minus, btn_zoom_plus, btn_up, btn_down, btn_left, btn_right):
                w.configure(state=state, fg=fg_controls)

            cell_now = self._cfg.cell_size_collapsed if is_collapsed else self._cfg.cell_size
            lbl_cell.configure(text=f"{int(cell_now)}px", fg=fg_controls)

            # Force a full repaint (helps with Windows compositing artifacts on overrideredirect popups)
            with suppress(Exception):
                popup.update_idletasks()
                popup.lift()
                popup.configure(bg=CARD_BG)

        _refresh()

    # -------- board cards --------

    def _select_board_card(self, idx: int) -> None:
        self.selected_board_idx = _clamp_int(idx, 0, max(0, len(self.boards) - 1), 0)
        self._refresh_lists()
        self.redraw()
        self._persist_state()

    def _get_view_switch_symbol(self) -> str:
        """Return the icon for the view switch button.

        The icon indicates the action that will happen when clicking:
        - Expand to full view when currently compact.
        - Collapse to compact view when currently full.
        """
        return "⤢" if self._cfg.is_collapsed else "⤡"

    def _refresh_view_switch_ui(self) -> None:
        """Refresh the mode label and view switch button state."""
        mode_text = "Compact View" if self._cfg.is_collapsed else "Full View"
        with suppress(Exception):
            self.lbl_mode.config(text=mode_text)

        btn = getattr(self, "btn_view_switch", None)
        if btn is not None:
            with suppress(Exception):
                btn.config(text=self._get_view_switch_symbol())

    def _toggle_collapsed_mode(self) -> None:
        """Toggle between Full and Collapsed Mode."""
        self._cfg.is_collapsed = not self._cfg.is_collapsed

        self._refresh_view_switch_ui()

        self.redraw()
        self._persist_state()

    def _refresh_lists(self) -> None:
        # Clear existing cards
        for w in self.board_container.winfo_children():
            w.destroy()

        # Update title
        if self.builds:
            b = self.builds[self.current_build_idx]
            title = str(b.get("profile") or "").strip()

            # Fallback: extract trailing [tag] from the build name
            if not title:
                nm = str(b.get("name") or "").strip()
                mt = re.search(r"\[([^\[\]]+)\]\s*$", nm)
                title = mt.group(1).strip() if mt else nm

            self.lbl_title.config(text=title or "Paragon")
        else:
            self.lbl_title.config(text="Paragon")

        if not self.boards:
            return

        # Create one card per board (no solid background block)
        for idx, bd in enumerate(self.boards):
            raw_name = str(bd.get("Name", "?") or "?")
            raw_rot = bd.get("Rotation", "0")
            raw_glyph = bd.get("Glyph")

            # Desired display:
            #   "Char" - "ParagonBoard" - "GlyphName" - "Rotation"
            # Example: Spiritborn - Starting Board - Spirit - 90°
            name_parts = raw_name.split("-", 1)
            char_slug = (name_parts[0] if name_parts else raw_name).strip().lower()
            board_slug = (name_parts[1] if len(name_parts) > 1 else raw_name).strip()

            char_map = {
                "paladin": "Paladin",
                "spiritborn": "Spiritborn",
                "necromancer": "Necromancer",
                "barbarian": "Barbarian",
                "druid": "Druid",
                "rogue": "Rogue",
                "sorcerer": "Sorcerer",
            }
            char_name = char_map.get(char_slug, char_slug.title() if char_slug else "?")
            board_name = board_slug.replace("-", " ").strip().title() if board_slug else "?"

            glyph_name = "No Glyph"
            if raw_glyph:
                g = str(raw_glyph).strip()
                g_parts = g.split("-", 1)
                if len(g_parts) > 1 and g_parts[0].strip().lower() == char_slug:
                    g = g_parts[1]
                glyph_name = g.replace("-", " ").strip().title() if g else "No Glyph"

            deg = parse_rotation(str(raw_rot))
            rot_text = f"{deg}°"

            text = f"{char_name} - {board_name} - {glyph_name} - {rot_text}"

            selected = idx == self.selected_board_idx
            bg = SELECT_BG if selected else CARD_BG
            fg = GOLD if selected else TEXT

            card = tk.Frame(self.board_container, bg=bg)
            card.pack(fill="x", pady=8)

            lbl = tk.Label(
                card,
                text=text,
                fg=fg,
                bg=bg,
                anchor="w",
                padx=14,
                pady=16,
                font=("Segoe UI", int(FS_BOARD_CARD * self._cfg.ui_scale), "bold"),
                wraplength=max(200, self._cfg.panel_w - 40),
                justify="left",
            )
            lbl.pack(fill="both", expand=True)
            lbl.bind("<Button-1>", lambda _, i=idx: self._select_board_card(i))
            card.bind("<Button-1>", lambda _, i=idx: self._select_board_card(i))

        with suppress(Exception):
            self.btn_build_menu.config(state=(tk.NORMAL if len(self.builds) > 1 else tk.DISABLED))

    # -------- input handlers --------

    def _on_boards_mousewheel(self, e: tk.Event) -> None:
        delta = 0
        if getattr(e, "delta", 0):
            delta = -1 if e.delta > 0 else 1
        elif getattr(e, "num", 0) in (4, 5):
            delta = -1 if e.num == 4 else 1

        if not delta:
            return

        # Scroll cards
        with suppress(Exception):
            self.boards_canvas.yview_scroll(int(delta), "units")

    def _on_grid_mousewheel(self, e: tk.Event) -> None:
        # Ignore if grid is locked
        if self._cfg.grid_locked:
            return

        delta = 0
        if getattr(e, "delta", 0):
            delta = 1 if e.delta > 0 else -1
        elif getattr(e, "num", 0) in (4, 5):
            delta = 1 if e.num == 4 else -1

        if not delta:
            return

        step = 1
        if getattr(e, "state", 0) & 0x0001:  # SHIFT
            step = 4

        # Modify cell_size based on current mode
        if self._cfg.is_collapsed:
            old = int(self._cfg.cell_size_collapsed)
            new = max(8, min(50, old + (step * delta)))
            if new == old:
                return

            # Keep grid stable under cursor while zooming
            mx, my = int(getattr(e, "x", 0)), int(getattr(e, "y", 0))
            rel_x = mx - int(self.grid_x_collapsed)
            rel_y = my - int(self.grid_y_collapsed)
            if old > 0:
                self.grid_x_collapsed = int(mx - (rel_x * new / old))
                self.grid_y_collapsed = int(my - (rel_y * new / old))

            self._cfg.cell_size_collapsed = new
        else:
            old = int(self._cfg.cell_size)
            new = max(10, min(80, old + (step * delta)))
            if new == old:
                return

            # Keep grid stable under cursor while zooming
            mx, my = int(getattr(e, "x", 0)), int(getattr(e, "y", 0))
            rel_x = mx - int(self.grid_x)
            rel_y = my - int(self.grid_y)
            if old > 0:
                self.grid_x = int(mx - (rel_x * new / old))
                self.grid_y = int(my - (rel_y * new / old))

            self._cfg.cell_size = new

        self.redraw()
        self._persist_state()

    def _move_grid(self, dx: int, dy: int) -> None:
        if self._cfg.grid_locked:
            return
        if self._cfg.is_collapsed:
            self.grid_x_collapsed += dx
            self.grid_y_collapsed += dy
        else:
            self.grid_x += dx
            self.grid_y += dy
        self.redraw()
        self._persist_state()

    def _zoom_grid(self, delta: int) -> None:
        if self._cfg.grid_locked:
            return
        if self._cfg.is_collapsed:
            old = int(self._cfg.cell_size_collapsed)
            new = max(8, min(50, old + delta))
            if new == old:
                return
            self._cfg.cell_size_collapsed = new
        else:
            old = int(self._cfg.cell_size)
            new = max(10, min(80, old + delta))
            if new == old:
                return
            self._cfg.cell_size = new
        self.redraw()
        self._persist_state()

    def _make_lock_image(self, locked: bool, size: int = 14) -> tk.PhotoImage | None:
        try:
            if Image is None:
                return None
            emoji = "🔒" if locked else "🔓"
            fnt = ImageFont.truetype(r"C:\Windows\Fonts\seguiemj.ttf", size)
            pad = 1
            img = Image.new("RGBA", (size + pad * 2, size + pad * 2), (0, 0, 0, 0))
            try:
                ImageDraw.Draw(img).text((pad, pad), emoji, font=fnt, embedded_color=True)
            except TypeError:
                ImageDraw.Draw(img).text((pad, pad), emoji, font=fnt)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return tk.PhotoImage(data=base64.b64encode(buf.getvalue()))
        except Exception:
            return None

    def _warmup_settings_assets(self) -> None:
        """Pre-create settings popup assets to avoid lag on first open.

        Currently this only caches the lock/unlock icons (PIL -> PhotoImage).
        """
        # Mark the scheduled callback as consumed (if any).
        self._warmup_after_id = None
        # If the window is already gone, do nothing.
        with suppress(Exception):
            if not self.winfo_exists():
                return
        # Avoid doing heavy work while the popup is open; try again shortly.
        if getattr(self, "_settings_popup", None) is not None:
            self._warmup_after_id = self.after(400, self._warmup_settings_assets)
            return
        if hasattr(self, "_lock_img_cache"):
            return
        icon_size = max(12, int(14 * self._cfg.ui_scale))
        self._lock_img_cache = {
            True: self._make_lock_image(True, icon_size),
            False: self._make_lock_image(False, icon_size),
        }

    def _on_grid_drag_start(self, e: tk.Event) -> None:
        self.focus_set()
        # Ignore if grid is locked
        if self._cfg.grid_locked:
            self._dragging_grid = False
            return

        if not self._is_on_gold_border(int(e.x), int(e.y)):
            self._dragging_grid = False
            return

        self._dragging_grid = True
        self._drag_start_xy = (int(e.x_root), int(e.y_root))

        # Use correct grid position based on mode
        if self._cfg.is_collapsed:
            self._drag_start_grid = (int(self.grid_x_collapsed), int(self.grid_y_collapsed))
        else:
            self._drag_start_grid = (int(self.grid_x), int(self.grid_y))

    def _on_grid_drag_move(self, e: tk.Event) -> None:
        if not self._dragging_grid:
            return

        sx, sy = self._drag_start_xy
        gx, gy = self._drag_start_grid
        dx = int(e.x_root) - sx
        dy = int(e.y_root) - sy

        # Update correct grid position based on mode
        if self._cfg.is_collapsed:
            self.grid_x_collapsed = gx + dx
            self.grid_y_collapsed = gy + dy
        else:
            self.grid_x = gx + dx
            self.grid_y = gy + dy

        self.redraw()

    def _on_grid_drag_end(self, _: tk.Event) -> None:
        if not self._dragging_grid:
            return

        self._dragging_grid = False
        self._persist_state()

    def _on_window_drag_start(self, e: tk.Event) -> None:
        self.focus_set()
        self._dragging_window = True
        self._win_drag_start_xy = (int(e.x_root), int(e.y_root))
        self._win_drag_start_pos = (int(self.winfo_x()), int(self.winfo_y()))

    def _on_window_drag_move(self, e: tk.Event) -> None:
        if not self._dragging_window:
            return

        sx, sy = self._win_drag_start_xy
        wx, wy = self._win_drag_start_pos
        dx = int(e.x_root) - sx
        dy = int(e.y_root) - sy

        self.geometry(f"+{wx + dx}+{wy + dy}")

    def _on_window_drag_end(self, _: tk.Event) -> None:
        if not self._dragging_window:
            return

        self._dragging_window = False
        self._persist_state()

    def _is_on_gold_border(self, x: int, y: int) -> bool:
        if not self._border_rect:
            return False

        x1, y1, x2, y2 = self._border_rect
        g = int(self._border_grab)
        if not (x1 - g <= x <= x2 + g and y1 - g <= y <= y2 + g):
            return False

        near = min(abs(x - x1), abs(x - x2), abs(y - y1), abs(y - y2))
        return near <= g

    # -------- helpers --------

    def _get_resolution(self) -> tuple[int, int]:
        with suppress(Exception):
            w, h = tuple(self._res.resolution)[:2]
            return (int(w), int(h))
        return (self.winfo_screenwidth(), self.winfo_screenheight())

    def _get_cam_roi(self) -> tuple[int, int, int, int] | None:
        roi = getattr(self._cam, "window_roi", None)
        if not roi:
            return None

        try:
            x, y, w, h = roi
            return (int(x), int(y), int(w), int(h))
        except Exception:
            return None

    def _apply_geometry(self) -> None:
        roi = self._get_cam_roi()
        if roi is not None:
            rx, ry, rw, rh = roi
        else:
            rw, rh = self._get_resolution()
            rx, ry = 0, 0

        # Use saved position if available.
        sx = self._settings.get("x")
        sy = self._settings.get("y")
        if isinstance(sx, int) and isinstance(sy, int):
            rx, ry = sx, sy

        self.geometry(f"{int(rw)}x{int(rh)}+{int(rx)}+{int(ry)}")

        with suppress(Exception):
            self.canvas.config(width=int(rw), height=int(rh))

    # -------- drawing --------

    def redraw(self) -> None:
        self.canvas.delete("all")

        if not self.boards:
            return

        board = self.boards[self.selected_board_idx]
        nodes = board.get("Nodes") or []

        if len(nodes) != NODES_LEN:
            return

        grid = nodes_to_grid(nodes)

        # Use settings based on current mode
        if self._cfg.is_collapsed:
            cs = int(self._cfg.cell_size_collapsed)
            gx0, gy0 = int(self.grid_x_collapsed), int(self.grid_y_collapsed)
        else:
            cs = int(self._cfg.cell_size)
            gx0, gy0 = int(self.grid_x), int(self.grid_y)

        grid_px = GRID * cs
        border_pad = 6
        border_w = 6

        self.canvas.create_rectangle(
            gx0 - border_pad,
            gy0 - border_pad,
            gx0 + grid_px + border_pad,
            gy0 + grid_px + border_pad,
            outline=GOLD,
            width=border_w,
        )

        self._border_rect = (
            int(gx0 - border_pad),
            int(gy0 - border_pad),
            int(gx0 + grid_px + border_pad),
            int(gy0 + grid_px + border_pad),
        )
        self._border_grab = max(12, (border_w * 2) + 2)

        # (removed) hint/status box above the grid

        # Grid lines
        for i in range(GRID + 1):
            p = i * cs
            self.canvas.create_line(gx0, gy0 + p, gx0 + grid_px, gy0 + p, fill="#3f3f3f", width=1)
            self.canvas.create_line(gx0 + p, gy0, gx0 + p, gy0 + grid_px, fill="#3f3f3f", width=1)

        # Nodes (transparent green boxes)
        inset = max(2, cs // 4)
        outline_w = max(2, cs // 10)

        node_outline = NODE_BLUE if self._is_colorblind_enabled() else NODE_GREEN

        for y in range(GRID):
            for x in range(GRID):
                if not grid[y][x]:
                    continue

                x1 = gx0 + x * cs + inset
                y1 = gy0 + y * cs + inset
                x2 = gx0 + (x + 1) * cs - inset
                y2 = gy0 + (y + 1) * cs - inset

                self.canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=TRANSPARENT_KEY,  # Transparent!
                    outline=node_outline,
                    width=outline_w,
                )

    # -------- lifecycle --------

    def close(self) -> None:
        try:
            self._persist_state()
            self.destroy()
        finally:
            if self._on_close:
                self._on_close()

            with _OVERLAY_LOCK:
                global _CURRENT_OVERLAY
                if _CURRENT_OVERLAY is self:
                    _CURRENT_OVERLAY = None

    def _persist_state(self) -> None:
        try:
            prof = ""
            if self.builds:
                prof = str(self.builds[self.current_build_idx].get("profile") or "")

            _save_overlay_settings({
                "x": int(self.winfo_x()),
                "y": int(self.winfo_y()),
                "cell_size": int(self._cfg.cell_size),
                "profile": prof,
                "build_idx": int(self.current_build_idx),
                "board_idx": int(self.selected_board_idx),
                "grid_x": int(self.grid_x),
                "grid_y": int(self.grid_y),
                # Collapsed mode
                "is_collapsed": bool(self._cfg.is_collapsed),
                "cell_size_collapsed": int(self._cfg.cell_size_collapsed),
                "grid_x_collapsed": int(self.grid_x_collapsed),
                "grid_y_collapsed": int(self.grid_y_collapsed),
                # Grid lock
                "grid_locked": bool(self._cfg.grid_locked),
            })
        except Exception:
            LOGGER.debug("Failed to persist overlay state", exc_info=True)


# ----------------------------
# Public API (used by app)
# ----------------------------


def run_paragon_overlay(preset_path: str | None = None, *, parent: tk.Misc | None = None) -> ParagonOverlay | None:
    """Start overlay in-process."""
    preset = preset_path or (sys.argv[1] if len(sys.argv) > 1 else None)

    try:
        builds = load_builds_from_path(preset)
        if not builds:
            LOGGER.warning("No Paragon data found in loaded profiles.")
            return None
    except Exception:
        LOGGER.exception("Failed to load Paragon preset(s): %s", preset)
        return None

    owns_root = False
    if parent is None:
        _enable_windows_dpi_awareness()
        root = tk.Tk()
        root.withdraw()
        parent = root
        owns_root = True

    overlay = ParagonOverlay(parent, builds, on_close=(parent.quit if owns_root else None))

    with _OVERLAY_LOCK:
        global _CURRENT_OVERLAY
        _CURRENT_OVERLAY = overlay
        _CLOSE_REQUESTED.clear()

    if owns_root:
        parent.mainloop()

    return overlay


def request_close(overlay: ParagonOverlay | None = None) -> None:
    """Request the Paragon overlay to close.

    Safe to call from non-Tk threads (hotkey thread). The overlay checks this
    flag periodically and closes itself.
    """
    with _OVERLAY_LOCK:
        target = overlay or _CURRENT_OVERLAY
        if target is None:
            return
        _CLOSE_REQUESTED.set()


if __name__ == "__main__":
    run_paragon_overlay()
