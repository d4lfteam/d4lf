"""Paragon overlay (tkinter)."""

from __future__ import annotations

import base64
import configparser
import ctypes
import io
import logging
import queue
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

from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import ProfileModel
from src.config.ui import ResManager
from src.item.filter import _UniqueKeyLoader

if TYPE_CHECKING:
    from collections.abc import Callable

LOGGER = logging.getLogger(__name__)

# =============================================================================
# GLOBALS & UI THREAD HANDLING
# =============================================================================

_CURRENT_OVERLAY: ParagonOverlay | None = None
_CLOSE_REQUESTED = threading.Event()
_OVERLAY_LOCK = threading.Lock()

_UI_THREAD: threading.Thread | None = None
_UI_QUEUE: queue.Queue[tuple[object, threading.Event | None, dict[str, object]]] = queue.Queue()
_UI_ROOT: tk.Tk | None = None
_UI_READY = threading.Event()


def _tk_thread_main() -> None:
    global _UI_ROOT
    with suppress(Exception):
        _enable_windows_dpi_awareness()
    root = tk.Tk()
    root.withdraw()
    _UI_ROOT = root
    _UI_READY.set()

    def _pump_queue() -> None:
        while True:
            try:
                fn, done, box = _UI_QUEUE.get_nowait()
            except queue.Empty:
                break

            try:
                box["result"] = fn()  # type: ignore[operator]
            except Exception as exc:
                box["error"] = exc
            finally:
                if done:
                    done.set()

        root.after(25, _pump_queue)

    root.after(0, _pump_queue)
    root.mainloop()


def _ensure_ui_thread() -> None:
    global _UI_THREAD
    if _UI_THREAD and _UI_THREAD.is_alive():
        return
    _UI_READY.clear()
    _UI_THREAD = threading.Thread(target=_tk_thread_main, name="paragon-overlay-ui", daemon=True)
    _UI_THREAD.start()
    if not _UI_READY.wait(timeout=5.0):
        msg = "Tk UI thread failed to init"
        raise RuntimeError(msg)


def _call_on_ui_thread(fn: object) -> object:
    _ensure_ui_thread()
    done, box = threading.Event(), {}
    _UI_QUEUE.put((fn, done, box))
    done.wait()
    exc = box.get("error")
    if isinstance(exc, BaseException):
        raise exc
    return box.get("result")


def _post_to_ui_thread(fn: object) -> None:
    _ensure_ui_thread()
    _UI_QUEUE.put((fn, None, {}))


def _is_alive(w: tk.Misc | None, mapped: bool = False) -> bool:
    """Helper to safely check if a widget exists (and optionally is mapped)."""
    try:
        return bool(w and w.winfo_exists() and (w.winfo_ismapped() if mapped else True))
    except Exception:
        return False


# =============================================================================
# THEME & CONSTANTS
# =============================================================================

TRANSPARENT_KEY = "#ff00ff"
CARD_BG = "#151515"
TEXT = "#ffffff"
MUTED = "#cfcfcf"
FS_ACCENT_GREEN = "#34C410"
FS_ACCENT_BLUE = "#56B4E9"
FS_ACCENT_GOLD = "#cfa15b"
FS_GRID_COLOR = "#3f3f3f"

GOLD = FS_ACCENT_GOLD
SELECT_BG = "#1f1f1f"
NODE_GREEN = FS_ACCENT_GREEN
NODE_BLUE = FS_ACCENT_BLUE

FS_PANEL_TITLE, FS_MODE_LABEL, FS_BUTTON, FS_BOARD_CARD = 13, 9, 12, 10
FS_BUILDS_MENU, FS_SETTINGS_ICON, FS_SETTINGS_LABEL, FS_ZOOM_BTN, FS_HINT = (12, 13, 10, 15, 10)
FS_CARD_FRAME, FS_GRID_FRAME = 1, 6

PANEL_W, GRID = 370, 21
NODES_LEN = GRID * GRID


# =============================================================================
# UI FACTORY HELPERS
# =============================================================================


def _tk_btn(parent: tk.Misc, text: str = "", cmd: Callable | None = None, **kw) -> tk.Button:
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
    return tk.Button(parent, text=text, command=cmd, **opts)


def _tk_lbl(parent: tk.Misc, text: str = "", **kw) -> tk.Label:
    """Creates a pre-styled Tkinter Label."""
    opts = {"bg": CARD_BG, "fg": TEXT}
    opts.update(kw)
    return tk.Label(parent, text=text, **opts)


# =============================================================================
# WINDOWS DPI HELPERS
# =============================================================================

_TK_BASELINE_SCALING = 96 / 72


def _enable_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return

    funcs = (
        lambda: ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)),
        lambda: ctypes.windll.shcore.SetProcessDpiAwareness(2),
        lambda: ctypes.windll.user32.SetProcessDPIAware(),
    )
    for func in funcs:
        try:
            func()
        except Exception as exc:
            LOGGER.debug("DPI awareness call failed: %s", exc, exc_info=True)
            continue
        else:
            return


def _dpi_scale_for_widget(w: tk.Misc) -> float:
    with suppress(Exception):
        return float(ctypes.windll.user32.GetDpiForWindow(int(w.winfo_id()))) / 96.0
    with suppress(Exception):
        return float(w.tk.call("tk", "scaling")) * 72 / 96.0
    return 1.0


# =============================================================================
# SETTINGS & DATA LOADERS
# =============================================================================


def _params_ini_path() -> Path:
    p = Path.home() / ".d4lf"
    p.mkdir(parents=True, exist_ok=True)
    return p / "params.ini"


def _load_overlay_settings() -> dict[str, Any]:
    ini = _params_ini_path()
    if not ini.exists():
        ini.write_text("", encoding="utf-8")
    p = configparser.ConfigParser()
    p.read(ini, encoding="utf-8")
    sec = p["paragon_overlay"] if p.has_section("paragon_overlay") else {}

    def parse(k: str, t: type) -> Any:
        v = sec.get(k)
        if not v:
            return None
        v = str(v).strip()
        if t is bool:
            if v.lower() in ("true", "1", "yes", "on"):
                return True
            if v.lower() in ("false", "0", "no", "off"):
                return False
            return None  # unbekannter Wert → Default verwenden
        try:
            return t(v)
        except Exception:
            return None

    return {
        "cell_size": parse("cell_size", int),
        "profile": parse("profile", str),
        "build_idx": parse("build_idx", int),
        "board_idx": parse("board_idx", int),
        "grid_x": parse("grid_x", int),
        "grid_y": parse("grid_y", int),
        "is_collapsed": parse("is_collapsed", bool),
        "cell_size_collapsed": parse("cell_size_collapsed", int),
        "grid_x_collapsed": parse("grid_x_collapsed", int),
        "grid_y_collapsed": parse("grid_y_collapsed", int),
        "grid_locked": parse("grid_locked", bool),
        "gold_frames": parse("gold_frames", bool),
    }


def _save_overlay_settings(values: dict[str, Any]) -> None:
    ini, p = _params_ini_path(), configparser.ConfigParser()
    if not ini.exists():
        ini.write_text("", encoding="utf-8")
    p.read(ini, encoding="utf-8")
    if not p.has_section("paragon_overlay"):
        p.add_section("paragon_overlay")
    for k, v in values.items():
        if v is not None:
            p["paragon_overlay"][str(k)] = str(v)
    with ini.open("w", encoding="utf-8") as f:
        p.write(f)


def _clamp_int(v: int | None, lo: int, hi: int, default: int) -> int:
    try:
        return max(lo, min(hi, int(v))) if v is not None else default
    except Exception:
        return default


def _iter_paragon_payloads(paragon: object) -> list[dict[str, Any]]:
    return (
        [paragon]
        if isinstance(paragon, dict)
        else [x for x in paragon if isinstance(x, dict)]
        if isinstance(paragon, list)
        else []
    )


def _load_profile_model(profile_path: Path, profile_name: str) -> ProfileModel | None:
    try:
        with profile_path.open(encoding="utf-8") as f:
            cfg = yaml.load(stream=f, Loader=_UniqueKeyLoader)
        if isinstance(cfg, dict):
            return ProfileModel(name=profile_name, **cfg)
    except Exception:
        LOGGER.debug("Profile load failed: %s", profile_path, exc_info=True)
    return None


def load_builds_from_path(preset_path: str | None = None) -> list[dict[str, Any]]:
    config = IniConfigLoader()
    profiles_dir = config.user_dir / "profiles"
    names = [p.strip() for p in config.general.profiles if p.strip()]
    candidates: list[tuple[str, Path]] = []

    if names:
        for n in names:
            p_yaml, p_yml = profiles_dir / f"{n}.yaml", profiles_dir / f"{n}.yml"
            if p_yaml.is_file():
                candidates.append((n, p_yaml))
            elif p_yml.is_file():
                candidates.append((n, p_yml))
            else:
                LOGGER.debug("Profile not found: %s", p_yaml)
    else:
        sd = Path(preset_path) if preset_path else profiles_dir
        if sd.is_file():
            sd = sd.parent
        candidates.extend([
            (fp.stem, fp) for fp in sorted(sd.glob("*.ya*"), key=lambda x: x.stat().st_mtime, reverse=True)
        ])

    builds: list[dict[str, Any]] = []
    for pname, ppath in candidates:
        model = _load_profile_model(ppath, pname)
        if not model or not model.Paragon:
            continue
        for payload in _iter_paragon_payloads(model.Paragon):
            steps = payload.get("ParagonBoardsList", [])
            steps = (
                [s for s in steps if isinstance(s, list) and s]
                if steps and isinstance(steps[0], list)
                else [steps]
                if steps
                else []
            )
            bname = payload.get("Name") or payload.get("name") or "Unknown Build"
            for idx in range(len(steps) - 1, -1, -1):
                sname = f"{bname} - Step {idx + 1}" if len(steps) > 1 else bname
                builds.append({"name": sname, "boards": steps[idx], "profile": pname})
    return builds


def parse_rotation(rot_str: str) -> int:
    m = re.search(r"(\d+)", rot_str or "")
    deg = int(m.group(1)) % 360 if m else 0
    return deg if deg in (0, 90, 180, 270) else 0


def nodes_to_grid(nodes: list[int] | list[bool]) -> list[list[bool]]:
    return [[bool(nodes[y * GRID + x]) for x in range(GRID)] for y in range(GRID)]


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass(slots=True)
class OverlayConfig:
    cell_size: int = 24
    grid_x_default: int = PANEL_W + 24
    grid_y_default: int = 24

    cell_size_collapsed: int = 16
    grid_x_collapsed_default: int = 600
    grid_y_collapsed_default: int = 300

    ui_scale: float = 1.0
    panel_w: int = PANEL_W
    poll_ms: int = 500
    window_alpha: float = 0.86

    is_collapsed: bool = False
    grid_locked: bool = False
    gold_frames: bool = False


# =============================================================================
# PARAGON OVERLAY CLASS
# =============================================================================


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

        self._cfg.cell_size = _clamp_int(self._settings.get("cell_size"), 10, 80, self._cfg.cell_size)
        self._cfg.cell_size_collapsed = _clamp_int(
            self._settings.get("cell_size_collapsed"), 8, 50, self._cfg.cell_size_collapsed
        )
        for key, attr in (
            ("is_collapsed", "is_collapsed"),
            ("grid_locked", "grid_locked"),
            ("gold_frames", "gold_frames"),
        ):
            val = self._settings.get(key)
            if isinstance(val, bool):
                setattr(self._cfg, attr, val)

        self._on_close = on_close
        self._cam = Cam()
        self._res = ResManager()
        self.builds = list(builds)

        prof, b_idx = self._settings.get("profile"), self._settings.get("build_idx")
        idx = next((i for i, b in enumerate(self.builds) if b.get("profile") == prof), b_idx) if prof else b_idx
        self.current_build_idx = _clamp_int(idx, 0, max(0, len(self.builds) - 1), 0)
        self.boards = self.builds[self.current_build_idx]["boards"] if self.builds else []
        self.selected_board_idx = _clamp_int(self._settings.get("board_idx"), 0, max(0, len(self.boards) - 1), 0)

        gx_val = self._settings.get("grid_x")
        gy_val = self._settings.get("grid_y")
        gxc_val = self._settings.get("grid_x_collapsed")
        gyc_val = self._settings.get("grid_y_collapsed")
        self.grid_x = gx_val if isinstance(gx_val, int) else (self._cfg.panel_w + 24)
        self.grid_y = gy_val if isinstance(gy_val, int) else 24
        self.grid_x_collapsed = gxc_val if isinstance(gxc_val, int) else self._cfg.grid_x_collapsed_default
        self.grid_y_collapsed = gyc_val if isinstance(gyc_val, int) else self._cfg.grid_y_collapsed_default

        (self._last_roi, self._last_res, self._border_rect, self._dragging_grid, self._border_grab) = (
            None,
            None,
            None,
            False,
            12,
        )

        self.title("D4LF Paragon Overlay")
        self.attributes("-topmost", True)
        with suppress(tk.TclError):
            self.attributes("-alpha", float(self._cfg.window_alpha))
            self.overrideredirect(True)
            self.wm_attributes("-transparentcolor", TRANSPARENT_KEY)
        self.configure(bg=TRANSPARENT_KEY)
        self.protocol("WM_DELETE_WINDOW", self.close)

        self._build_ui()
        self._bind_events()
        self._apply_geometry()
        self._refresh_lists()
        self.redraw()

        self._warmup_after_id = self.after(600, self._warmup_settings_assets)
        self.after(self._cfg.poll_ms, self._poll_window_state)
        self.after(50, self._poll_close_request)

    def _apply_dpi_scaling(self) -> None:
        with suppress(Exception):
            self.tk.call("tk", "scaling", _TK_BASELINE_SCALING)
        scale = _dpi_scale_for_widget(self) * float(self._cfg.ui_scale or 1.0)
        self._cfg.ui_scale = eff = max(0.75, min(4.0, float(scale)))

        self._cfg.panel_w = round(self._cfg.panel_w * eff)
        if self._settings.get("cell_size") is None:
            self._cfg.cell_size = round(self._cfg.cell_size * eff)
        if self._settings.get("cell_size_collapsed") is None:
            self._cfg.cell_size_collapsed = round(self._cfg.cell_size_collapsed * eff)

    # --- UI LAYOUT ---

    def _build_ui(self) -> None:
        accent = self._accent_frame_color()
        outer = tk.Frame(self, bg=TRANSPARENT_KEY)
        outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(outer, highlightthickness=0, bg=TRANSPARENT_KEY)
        self.canvas.pack(fill="both", expand=True)

        self.left = tk.Frame(outer, bg=TRANSPARENT_KEY)
        self.left.place(x=0, y=0, width=self._cfg.panel_w, relheight=1.0)

        # Title Card
        self.card_title = tk.Frame(
            self.left,
            bg=CARD_BG,
            highlightthickness=self._accent_frame_thickness(),
            highlightbackground=accent,
            highlightcolor=accent,
        )
        self.card_title.pack(
            fill="x",
            padx=int(10 * self._cfg.ui_scale),
            pady=(int(10 * self._cfg.ui_scale), int(8 * self._cfg.ui_scale)),
        )

        title_row = tk.Frame(self.card_title, bg=CARD_BG)
        title_row.pack(
            fill="both", expand=True, padx=int(12 * self._cfg.ui_scale), pady=(0, int(4 * self._cfg.ui_scale))
        )

        self.lbl_title = _tk_lbl(
            title_row,
            font=("Segoe UI", int(FS_PANEL_TITLE * self._cfg.ui_scale), "bold"),
            anchor="w",
            wraplength=max(200, self._cfg.panel_w - 40),
            justify="left",
        )
        self.lbl_title.pack(side="left", fill="x", expand=True)

        mode_frame = tk.Frame(self.card_title, bg=CARD_BG)
        mode_frame.pack(fill="x", padx=int(12 * self._cfg.ui_scale))

        self.lbl_mode = _tk_lbl(
            mode_frame,
            text="Compact View" if self._cfg.is_collapsed else "Full View",
            fg=MUTED,
            font=("Segoe UI", int(FS_MODE_LABEL * self._cfg.ui_scale)),
            anchor="w",
        )
        self.lbl_mode.pack(side="left")

        self.btn_view_switch = _tk_btn(
            mode_frame,
            text="⤢" if self._cfg.is_collapsed else "⤡",
            cmd=self._toggle_collapsed_mode,
            font=("Segoe UI", int(FS_BUTTON * self._cfg.ui_scale), "bold"),
            padx=int(8 * self._cfg.ui_scale),
            pady=int(2 * self._cfg.ui_scale),
        )
        self.btn_view_switch.pack(side="left", padx=(int(8 * self._cfg.ui_scale), 0))

        # Buttons Card
        self.card_buttons = tk.Frame(
            self.left,
            bg=CARD_BG,
            highlightthickness=self._accent_frame_thickness(),
            highlightbackground=accent,
            highlightcolor=accent,
        )
        self.card_buttons.pack(fill="x", padx=int(10 * self._cfg.ui_scale), pady=(0, int(8 * self._cfg.ui_scale)))

        btn_cont = tk.Frame(self.card_buttons, bg=CARD_BG)
        btn_cont.pack(expand=True, fill="both", padx=int(12 * self._cfg.ui_scale), pady=int(8 * self._cfg.ui_scale))

        self.btn_settings = _tk_btn(
            btn_cont,
            text="ParagonOverlay⚙ ▼",
            cmd=self._show_settings_dropdown,
            font=("Segoe UI", int(FS_BUTTON * self._cfg.ui_scale), "bold"),
            padx=int(10 * self._cfg.ui_scale),
            pady=int(6 * self._cfg.ui_scale),
        )
        self.btn_settings.pack(side="left", padx=int(4 * self._cfg.ui_scale))

        self.btn_build_menu = _tk_btn(
            btn_cont,
            text="Builds ▼",
            cmd=self._show_build_menu,
            font=("Segoe UI", int(FS_BUTTON * self._cfg.ui_scale), "bold"),
            padx=int(12 * self._cfg.ui_scale),
            pady=int(6 * self._cfg.ui_scale),
        )
        self.btn_build_menu.pack(side="right", padx=int(5 * self._cfg.ui_scale))

        # Boards Scroll Area
        self.boards_canvas = tk.Canvas(self.left, bg=TRANSPARENT_KEY, highlightthickness=0)
        self.boards_canvas.pack(
            fill="both", expand=True, padx=int(10 * self._cfg.ui_scale), pady=(0, int(12 * self._cfg.ui_scale))
        )
        self.board_container = tk.Frame(self.boards_canvas, bg=TRANSPARENT_KEY)
        self._boards_window_id = self.boards_canvas.create_window((0, 0), window=self.board_container, anchor="nw")

        self.board_container.bind(
            "<Configure>", lambda *_: self.boards_canvas.configure(scrollregion=self.boards_canvas.bbox("all"))
        )
        self.boards_canvas.bind(
            "<Configure>", lambda e: self.boards_canvas.itemconfigure(self._boards_window_id, width=int(e.width))
        )

    def _bind_events(self) -> None:
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.boards_canvas.bind(ev, self._on_boards_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self._on_grid_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_grid_drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_grid_drag_end)

    # --- POLLING & STATE MANAGEMENT ---

    def _poll_close_request(self) -> None:
        if _CLOSE_REQUESTED.is_set():
            _CLOSE_REQUESTED.clear()
            self.close()
            return
        if _is_alive(self):
            self.after(50, self._poll_close_request)

    def _poll_window_state(self) -> None:
        try:
            roi, res = self._get_cam_roi(), self._get_resolution()
            if roi != self._last_roi or res != self._last_res:
                self._last_roi, self._last_res = roi, res
                self._apply_geometry()
                self.redraw()
        finally:
            self.after(self._cfg.poll_ms, self._poll_window_state)

    def _select_build(self, idx: int) -> None:
        if not self.builds:
            return
        self.current_build_idx = _clamp_int(idx, 0, max(0, len(self.builds) - 1), 0)
        self.boards = self.builds[self.current_build_idx]["boards"] if self.builds else []
        self.selected_board_idx = 0
        self._refresh_lists()
        self.redraw()
        self._persist_state()

    def _toggle_grid_lock(self) -> None:
        self._cfg.grid_locked = not self._cfg.grid_locked
        self._persist_state()

    def _toggle_gold_frames(self) -> None:
        self._cfg.gold_frames = not getattr(self._cfg, "gold_frames", False)
        self._persist_state()
        self._apply_accent_frames(force=True)
        self.redraw()

    def _reset_grid_defaults(self) -> None:
        s = float(self._cfg.ui_scale or 1.0)
        self._cfg.cell_size, self._cfg.cell_size_collapsed = (
            _clamp_int(round(24 * s), 10, 80, self._cfg.cell_size),
            _clamp_int(round(16 * s), 8, 50, self._cfg.cell_size_collapsed),
        )
        self.grid_x, self.grid_y = self._cfg.panel_w + round(24 * s), round(24 * s)
        self.grid_x_collapsed, self.grid_y_collapsed = (
            self._cfg.grid_x_collapsed_default,
            self._cfg.grid_y_collapsed_default,
        )
        self._persist_state()
        self.redraw()

    def _accent_frame_color(self) -> str:
        if getattr(self._cfg, "gold_frames", False):
            return GOLD
        try:
            return NODE_BLUE if bool(getattr(IniConfigLoader().general, "colorblind_mode", False)) else NODE_GREEN
        except Exception:
            return NODE_GREEN

    def _accent_frame_thickness(self) -> int:
        return max(1, round(FS_CARD_FRAME * float(self._cfg.ui_scale or 1.0)))

    def _grid_frame_thickness(self) -> int:
        return max(1, round(FS_GRID_FRAME * float(self._cfg.ui_scale or 1.0)))

    def _apply_accent_frames(self, *, force: bool = False) -> None:
        c = self._accent_frame_color()
        if not force and getattr(self, "_accent_frame_last", None) == c:
            return
        self._accent_frame_last, th = c, self._accent_frame_thickness()

        for w in (getattr(self, "card_title", None), getattr(self, "card_buttons", None)):
            if _is_alive(w):
                with suppress(Exception):
                    w.configure(highlightthickness=th, highlightbackground=c, highlightcolor=c)

        bc = getattr(self, "board_container", None)
        if _is_alive(bc):
            for child in bc.winfo_children():
                if isinstance(child, tk.Frame):
                    with suppress(Exception):
                        child.configure(highlightthickness=th, highlightbackground=c, highlightcolor=c)

        for p in ("_settings_popup", "_build_popup"):
            if _is_alive(getattr(self, p, None)):
                getattr(self, p).configure(highlightthickness=th, highlightbackground=c, highlightcolor=c)

    def _reload_profiles(self) -> None:
        try:
            if not (new_builds := load_builds_from_path()):
                return
            self.builds = new_builds
            self.current_build_idx = self.current_build_idx if 0 <= self.current_build_idx < len(self.builds) else 0
            self.boards = self.builds[self.current_build_idx]["boards"] if self.builds else []
            self.selected_board_idx = min(self.selected_board_idx, max(0, len(self.boards) - 1))
            self._refresh_lists()
            self.redraw()
        except Exception:
            LOGGER.exception("Failed to reload profiles")

    # --- DROPDOWNS: BUILDS & SETTINGS ---

    def _is_descendant(self, child: tk.Misc, parent: tk.Misc) -> bool:
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

    def _close_popup(self, attr_name: str, btn_widget: tk.Button, escape_id_attr: str, click_id_attr: str) -> None:
        popup = getattr(self, attr_name, None)
        if popup:
            with suppress(Exception):
                popup.place_forget()
        with suppress(Exception):
            btn_widget.config(fg=TEXT)
        for attr, evt in ((click_id_attr, "<Button-1>"), (escape_id_attr, "<Escape>")):
            if bid := getattr(self, attr, None):
                with suppress(Exception):
                    self.unbind(evt, bid)
                setattr(self, attr, None)

    def _handle_global_click(self, e: tk.Event, attr_name: str, btn_widget: tk.Button, close_func: Callable) -> None:
        popup = getattr(self, attr_name, None)
        if not _is_alive(popup, mapped=True):
            return
        w = None
        with suppress(Exception):
            w = self.winfo_containing(e.x_root, e.y_root)
        if not w or (w is not btn_widget and not self._is_descendant(w, popup)):
            close_func()

    def _close_build_dropdown(self) -> None:
        self._close_popup("_build_popup", self.btn_build_menu, "_build_popup_escape_bind_id", "_build_popup_bind_id")

    def _close_settings_dropdown(self) -> None:
        self._close_popup(
            "_settings_popup", self.btn_settings, "_settings_popup_escape_bind_id", "_settings_popup_bind_id"
        )

    def _show_dropdown(
        self,
        popup_attr: str,
        btn_widget: tk.Button,
        build_func: Callable,
        close_func: Callable,
        escape_attr: str,
        click_attr: str,
        click_handler: Callable,
    ) -> None:
        if popup_attr == "_build_popup":
            self._close_settings_dropdown()
        else:
            self._close_build_dropdown()

        popup = getattr(self, popup_attr, None)
        if _is_alive(popup, mapped=True):
            close_func()
            return

        if popup_attr == "_settings_popup":
            if getattr(self, "_warmup_after_id", None):
                with suppress(Exception):
                    self.after_cancel(self._warmup_after_id)
                self._warmup_after_id = None
            if not hasattr(self, "_lock_img_cache"):
                self._warmup_settings_assets()

        if not _is_alive(popup):
            c = self._accent_frame_color()
            popup = tk.Frame(
                self,
                bg=CARD_BG,
                bd=0,
                highlightthickness=self._accent_frame_thickness(),
                highlightbackground=c,
                highlightcolor=c,
            )
            setattr(self, popup_attr, popup)
            setattr(self, f"{popup_attr}_refresh", build_func(popup))

        self._apply_accent_frames()
        if callable(refresh := getattr(self, f"{popup_attr}_refresh", None)):
            refresh()

        popup.place(x=-9999, y=-9999)  # off-screen messen ohne Flash
        self.update_idletasks()
        popup.update_idletasks()
        s = self._cfg.ui_scale

        pw = min(
            max(1, popup.winfo_reqwidth() if popup_attr == "_settings_popup" else popup.winfo_reqwidth() + int(46 * s)),
            max(1, self.winfo_width() - int(8 * s)),
        )
        ph = popup.winfo_reqheight()

        x, y = (
            btn_widget.winfo_rootx() - self.winfo_rootx(),
            btn_widget.winfo_rooty() - self.winfo_rooty() + btn_widget.winfo_height() + int(4 * s),
        )
        if x + pw > self.winfo_width():
            x = max(0, self.winfo_width() - pw - int(4 * s))
        if y + ph > self.winfo_height():
            y = max(0, btn_widget.winfo_rooty() - self.winfo_rooty() - ph - int(4 * s))

        popup.place(x=x, y=y, width=pw)
        popup.lift()
        with suppress(Exception):
            btn_widget.config(fg=GOLD)

        def _arm():
            if not getattr(self, click_attr, None):
                setattr(self, click_attr, self.bind("<Button-1>", click_handler, add="+"))
            if not getattr(self, escape_attr, None):
                setattr(self, escape_attr, self.bind("<Escape>", lambda *_: close_func(), add="+"))

        self.after_idle(_arm)
        return

    def _show_build_menu(self) -> None:
        if self.builds:
            self._show_dropdown(
                "_build_popup",
                self.btn_build_menu,
                self._build_build_popup,
                self._close_build_dropdown,
                "_build_popup_escape_bind_id",
                "_build_popup_bind_id",
                lambda e: self._handle_global_click(e, "_build_popup", self.btn_build_menu, self._close_build_dropdown),
            )

    def _show_settings_dropdown(self) -> None:
        self._show_dropdown(
            "_settings_popup",
            self.btn_settings,
            self._build_settings_popup,
            self._close_settings_dropdown,
            "_settings_popup_escape_bind_id",
            "_settings_popup_bind_id",
            lambda e: self._handle_global_click(e, "_settings_popup", self.btn_settings, self._close_settings_dropdown),
        )

    def _build_build_popup(self, host: tk.Misc) -> Any:
        scale = self._cfg.ui_scale
        c = tk.Frame(host, bg=CARD_BG, padx=int(12 * scale), pady=int(10 * scale))
        c.pack(fill="both", expand=True)
        max_h = int(360 * scale)
        cv = tk.Canvas(c, bg=CARD_BG, highlightthickness=0, bd=0, height=max_h)
        cv.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(c, orient="vertical", command=cv.yview)
        sb.pack(side="right", fill="y")
        cv.configure(yscrollcommand=sb.set)
        lf = tk.Frame(cv, bg=CARD_BG)
        wid = cv.create_window((0, 0), window=lf, anchor="nw")

        lf.bind("<Configure>", lambda *_: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfigure(wid, width=int(e.width)))

        def _ref():
            for w in lf.winfo_children():
                w.destroy()
            grps: dict[str, list[tuple[int, dict[str, Any]]]] = {}
            for i, b in enumerate(self.builds):
                grps.setdefault(str(b.get("profile") or "Ungrouped"), []).append((i, b))
            mul = len(grps) > 1

            for p in sorted(grps):
                if mul:
                    _tk_lbl(
                        lf,
                        text=p,
                        fg=MUTED,
                        font=("Segoe UI", int(FS_BUILDS_MENU * scale), "bold"),
                        anchor="w",
                        padx=int(6 * scale),
                        pady=int(6 * scale),
                    ).pack(fill="x", pady=(int(4 * scale), int(2 * scale)))
                for i, b in grps[p]:
                    act = i == self.current_build_idx
                    _tk_btn(
                        lf,
                        text=str(b.get("name") or "Unknown Build"),
                        cmd=lambda idx=i: (self._select_build(idx), self._close_build_dropdown()),
                        bg=SELECT_BG if act else CARD_BG,
                        fg=GOLD if act else TEXT,
                        anchor="w",
                        padx=int(10 * scale),
                        pady=int(6 * scale),
                        font=("Segoe UI", int(FS_BUILDS_MENU * scale), "bold" if act else "normal"),
                    ).pack(fill="x", pady=int(2 * scale))
                if mul:
                    tk.Frame(lf, bg=MUTED, height=1).pack(fill="x", pady=int(6 * scale))

            with suppress(Exception):
                host.update_idletasks()
                cv.configure(height=min(max_h, max(int(120 * scale), lf.winfo_reqheight())))
                cv.yview_moveto(0.0)

        return _ref  # initial fill done by caller via refresh()

    def _build_settings_popup(self, host: tk.Misc) -> Any:
        s = self._cfg.ui_scale
        c = tk.Frame(host, bg=CARD_BG, padx=int(14 * s), pady=int(10 * s))
        c.pack(fill="both", expand=True)
        imgs: dict[bool, tk.PhotoImage | None] = getattr(self, "_lock_img_cache", {})

        def _row(txt: str, img: tk.PhotoImage | None, lbl_txt: str, cmd: Callable) -> tuple[tk.Button, tk.Label]:
            r = tk.Frame(c, bg=CARD_BG)
            r.pack(fill="x", pady=int(3 * s))
            b = (
                _tk_btn(r, image=img, cmd=cmd, padx=int(6 * s), pady=int(4 * s))
                if img
                else _tk_btn(
                    r,
                    text=txt,
                    cmd=cmd,
                    font=("Segoe UI", int(FS_SETTINGS_ICON * s), "bold"),
                    padx=int(6 * s),
                    pady=int(4 * s),
                )
            )
            if img:
                b.image = img
            b.pack(side="left")
            lbl = _tk_lbl(r, text=lbl_txt, font=("Segoe UI", int(FS_SETTINGS_LABEL * s)), anchor="w")
            lbl.pack(side="left", padx=(int(8 * s), int(24 * s)))
            return b, lbl

        btn_lock, lbl_lock = _row(
            "🔒" if self._cfg.grid_locked else "🔓",
            imgs.get(self._cfg.grid_locked),
            "Grid locked",
            lambda: (self._toggle_grid_lock(), _ref()),
        )
        btn_gold, lbl_gold = _row("★", None, "Golden frames", lambda: (self._toggle_gold_frames(), _ref()))
        _row("↻", None, "Reload profiles", self._reload_profiles)
        _row("↺", None, "Reset grid defaults", lambda: (self._reset_grid_defaults(), _ref()))

        tk.Frame(c, bg=MUTED, height=1).pack(fill="x", pady=int(6 * s))

        # Zoom
        zr = tk.Frame(c, bg=CARD_BG)
        zr.pack(fill="x", pady=int(3 * s))
        btn_zm = _tk_btn(
            zr,
            text="−",
            cmd=lambda: (self._zoom_grid(-1), _ref()),
            font=("Segoe UI", int(FS_ZOOM_BTN * s), "bold"),
            padx=int(8 * s),
            pady=int(2 * s),
        )
        btn_zm.pack(side="left")
        lbl_cell = _tk_lbl(zr, font=("Segoe UI", int(FS_SETTINGS_LABEL * s), "bold"), width=5, anchor="center")
        lbl_cell.pack(side="left")
        btn_zp = _tk_btn(
            zr,
            text="+",
            cmd=lambda: (self._zoom_grid(1), _ref()),
            font=("Segoe UI", int(FS_ZOOM_BTN * s), "bold"),
            padx=int(8 * s),
            pady=int(2 * s),
        )
        btn_zp.pack(side="left")
        _tk_lbl(zr, text="Grid Zoom", fg=MUTED, font=("Segoe UI", int(FS_SETTINGS_LABEL * s)), anchor="w").pack(
            side="left", padx=(int(8 * s), 0)
        )

        tk.Frame(c, bg=MUTED, height=1).pack(fill="x", pady=int(4 * s))

        # D-Pad
        dp = tk.Frame(c, bg=CARD_BG)
        dp.pack(anchor="w", pady=(int(2 * s), int(2 * s)))
        dc = tk.Frame(dp, bg=CARD_BG)
        dc.pack(side="left")
        sp = int(30 * s)

        r0 = tk.Frame(dc, bg=CARD_BG)
        r0.pack()
        tk.Frame(r0, bg=CARD_BG, width=sp, height=1).pack(side="left")
        _tk_btn(
            r0,
            text="↑",
            cmd=lambda: (self._move_grid(0, -1), _ref()),
            font=("Segoe UI", int(FS_SETTINGS_ICON * s), "bold"),
            width=2,
            pady=int(2 * s),
        ).pack(side="left", padx=1, pady=1)
        tk.Frame(r0, bg=CARD_BG, width=sp, height=1).pack(side="left")

        r1 = tk.Frame(dc, bg=CARD_BG)
        r1.pack()
        _tk_btn(
            r1,
            text="←",
            cmd=lambda: (self._move_grid(-1, 0), _ref()),
            font=("Segoe UI", int(FS_SETTINGS_ICON * s), "bold"),
            width=2,
            pady=int(2 * s),
        ).pack(side="left", padx=1, pady=1)
        tk.Frame(r1, bg=CARD_BG, width=sp, height=1).pack(side="left")
        _tk_btn(
            r1,
            text="→",
            cmd=lambda: (self._move_grid(1, 0), _ref()),
            font=("Segoe UI", int(FS_SETTINGS_ICON * s), "bold"),
            width=2,
            pady=int(2 * s),
        ).pack(side="left", padx=1, pady=1)

        r2 = tk.Frame(dc, bg=CARD_BG)
        r2.pack()
        tk.Frame(r2, bg=CARD_BG, width=sp, height=1).pack(side="left")
        _tk_btn(
            r2,
            text="↓",
            cmd=lambda: (self._move_grid(0, 1), _ref()),
            font=("Segoe UI", int(FS_SETTINGS_ICON * s), "bold"),
            width=2,
            pady=int(2 * s),
        ).pack(side="left", padx=1, pady=1)
        tk.Frame(r2, bg=CARD_BG, width=sp, height=1).pack(side="left")

        _tk_lbl(dp, text="Move\nGrid", fg=MUTED, font=("Segoe UI", int(FS_HINT * s)), anchor="w", justify="left").pack(
            side="left", padx=(int(8 * s), 0)
        )
        tk.Frame(c, bg=MUTED, height=1).pack(fill="x", pady=int(6 * s))
        _tk_lbl(
            c,
            text="• Drag frame to move grid\n• D-Pad ↑ ↓ ← → moves grid per click\n• Use − + buttons to zoom\n• Use ★ to make all frames golden\n• Use ↺ to reset to default size/position\n• Use 🔓 to unlock/lock grid",
            fg=MUTED,
            font=("Segoe UI", int(FS_HINT * s)),
            anchor="w",
            justify="left",
            padx=int(4 * s),
            pady=int(6 * s),
        ).pack(fill="x")

        def _ref():
            lk, gd = self._cfg.grid_locked, getattr(self._cfg, "gold_frames", False)
            if imgs.get(lk):
                btn_lock.configure(image=imgs[lk])
                btn_lock.image = imgs[lk]
            else:
                btn_lock.configure(text="🔒" if lk else "🔓", fg=GOLD if lk else TEXT)
            lbl_lock.configure(text="Grid locked" if lk else "Grid unlocked", fg=GOLD if lk else TEXT)
            btn_gold.configure(fg=GOLD if gd else TEXT)
            lbl_gold.configure(text="Golden frames (on)" if gd else "Golden frames (off)", fg=GOLD if gd else TEXT)

            for w in (btn_zm, btn_zp) + tuple(dc.winfo_children()):
                for child in w.winfo_children():
                    if isinstance(child, tk.Button):
                        child.configure(state=tk.DISABLED if lk else tk.NORMAL, fg=MUTED if lk else TEXT)

            lbl_cell.configure(
                text=f"{int(self._cfg.cell_size_collapsed if self._cfg.is_collapsed else self._cfg.cell_size)}px",
                fg=MUTED if lk else TEXT,
            )
            with suppress(Exception):
                host.update_idletasks()
                host.lift()
                host.configure(bg=CARD_BG)

        _ref()
        return _ref

    # --- BOARD CARDS ---

    def _update_board_selection(self) -> None:
        """Recolor board cards in-place — no destroy/rebuild, no flicker."""
        for i, card in enumerate(self.board_container.winfo_children()):
            selected = i == self.selected_board_idx
            bg, fg = (SELECT_BG, GOLD) if selected else (CARD_BG, TEXT)
            with suppress(Exception):
                card.configure(bg=bg)
            for child in card.winfo_children():
                with suppress(Exception):
                    child.configure(bg=bg, fg=fg)

    def _select_board_card(self, idx: int) -> None:
        self.selected_board_idx = _clamp_int(idx, 0, max(0, len(self.boards) - 1), 0)
        self._update_board_selection()
        self.redraw()
        self._persist_state()

    def _toggle_collapsed_mode(self) -> None:
        self._cfg.is_collapsed = not self._cfg.is_collapsed
        with suppress(Exception):
            self.lbl_mode.config(text="Compact View" if self._cfg.is_collapsed else "Full View")
        if _is_alive(getattr(self, "btn_view_switch", None)):
            self.btn_view_switch.config(text="⤢" if self._cfg.is_collapsed else "⤡")
        self.redraw()
        self._persist_state()

    def _refresh_lists(self) -> None:
        for w in self.board_container.winfo_children():
            w.destroy()

        t = "Paragon"
        if self.builds:
            b = self.builds[self.current_build_idx]
            t = str(b.get("profile") or "").strip()
            if not t:
                nm = str(b.get("name") or "").strip()
                mt = re.search(r"\[([^\[\]]+)\]\s*$", nm)
                t = mt.group(1).strip() if mt else nm
        self.lbl_title.config(text=t or "Paragon")

        if not self.boards:
            return
        acc = self._accent_frame_color()

        for idx, bd in enumerate(self.boards):
            rn, rg = str(bd.get("Name", "?") or "?"), bd.get("Glyph")
            np = rn.split("-", 1)
            cs, bs = ((np[0] if np else rn).strip().lower(), (np[1] if len(np) > 1 else rn).strip())
            cn = {
                "paladin": "Paladin",
                "spiritborn": "Spiritborn",
                "necromancer": "Necromancer",
                "barbarian": "Barbarian",
                "druid": "Druid",
                "rogue": "Rogue",
                "sorcerer": "Sorcerer",
            }.get(cs, cs.title() if cs else "?")
            gn = "No Glyph"
            if rg:
                gp = str(rg).strip().split("-", 1)
                g = gp[1] if len(gp) > 1 and gp[0].strip().lower() == cs else str(rg).strip()
                gn = g.replace("-", " ").strip().title() if g else "No Glyph"

            txt = f"{cn} - {bs.replace('-', ' ').strip().title() if bs else '?'} - {gn} - {parse_rotation(str(bd.get('Rotation', '0')))}°"
            sel = idx == self.selected_board_idx
            bg, fg = (SELECT_BG, GOLD) if sel else (CARD_BG, TEXT)

            c = tk.Frame(
                self.board_container,
                bg=bg,
                highlightthickness=self._accent_frame_thickness(),
                highlightbackground=acc,
                highlightcolor=acc,
            )
            c.pack(fill="x", pady=8)
            lbl = _tk_lbl(
                c,
                text=txt,
                fg=fg,
                bg=bg,
                anchor="w",
                font=("Segoe UI", int(FS_BOARD_CARD * self._cfg.ui_scale), "bold"),
                wraplength=max(200, self._cfg.panel_w - 40),
                justify="left",
            )
            lbl.pack(fill="both", expand=True, padx=14, pady=16)
            lbl.bind("<Button-1>", lambda _e, i=idx: self._select_board_card(i))
            c.bind("<Button-1>", lambda _e, i=idx: self._select_board_card(i))

        self._apply_accent_frames()
        with suppress(Exception):
            self.btn_build_menu.config(state=(tk.NORMAL if len(self.builds) > 1 else tk.DISABLED))

    # --- EVENT HANDLERS ---

    def _on_boards_mousewheel(self, e: tk.Event) -> None:
        delta = (
            -1
            if getattr(e, "delta", 0) > 0 or getattr(e, "num", 0) == 4
            else 1
            if getattr(e, "delta", 0) < 0 or getattr(e, "num", 0) == 5
            else 0
        )
        if delta:
            with suppress(Exception):
                self.boards_canvas.yview_scroll(int(delta), "units")

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
            self._cfg.cell_size_collapsed = max(8, min(50, self._cfg.cell_size_collapsed + delta))
        else:
            self._cfg.cell_size = max(10, min(80, self._cfg.cell_size + delta))
        self.redraw()
        self._persist_state()

    def _warmup_settings_assets(self) -> None:
        self._warmup_after_id = None
        if not _is_alive(self) or hasattr(self, "_lock_img_cache"):
            return
        if _is_alive(getattr(self, "_settings_popup", None), mapped=True):
            self._warmup_after_id = self.after(400, self._warmup_settings_assets)
            return

        sz = max(12, int(14 * self._cfg.ui_scale))
        if not Image or not ImageFont or not ImageDraw:
            self._lock_img_cache = {True: None, False: None}
            return

        try:
            fnt = ImageFont.truetype(r"C:\Windows\Fonts\seguiemj.ttf", sz)

            def _mk(locked: bool) -> tk.PhotoImage:
                i = Image.new("RGBA", (sz + 2, sz + 2), (0, 0, 0, 0))
                try:
                    ImageDraw.Draw(i).text((1, 1), "🔒" if locked else "🔓", font=fnt, embedded_color=True)
                except TypeError:
                    ImageDraw.Draw(i).text((1, 1), "🔒" if locked else "🔓", font=fnt)
                b = io.BytesIO()
                i.save(b, format="PNG")
                return tk.PhotoImage(data=base64.b64encode(b.getvalue()))

            self._lock_img_cache = {True: _mk(True), False: _mk(False)}
        except Exception:
            self._lock_img_cache = {True: None, False: None}

    def _on_grid_drag_start(self, e: tk.Event) -> None:
        self.focus_set()
        if self._cfg.grid_locked or not self._border_rect:
            self._dragging_grid = False
            return
        x1, y1, x2, y2, g, x, y = (*self._border_rect, int(self._border_grab), int(e.x), int(e.y))
        if (
            not (x1 - g <= x <= x2 + g and y1 - g <= y <= y2 + g)
            or min(abs(x - x1), abs(x - x2), abs(y - y1), abs(y - y2)) > g
        ):
            self._dragging_grid = False
            return

        self._dragging_grid, self._drag_start_xy = True, (int(e.x_root), int(e.y_root))
        self._drag_start_grid = (
            (int(self.grid_x_collapsed), int(self.grid_y_collapsed))
            if self._cfg.is_collapsed
            else (int(self.grid_x), int(self.grid_y))
        )

    def _on_grid_drag_move(self, e: tk.Event) -> None:
        if not self._dragging_grid:
            return
        dx, dy = (int(e.x_root) - self._drag_start_xy[0], int(e.y_root) - self._drag_start_xy[1])
        if self._cfg.is_collapsed:
            self.grid_x_collapsed, self.grid_y_collapsed = (
                self._drag_start_grid[0] + dx,
                self._drag_start_grid[1] + dy,
            )
        else:
            self.grid_x, self.grid_y = (self._drag_start_grid[0] + dx, self._drag_start_grid[1] + dy)
        self.redraw()

    def _on_grid_drag_end(self, _: tk.Event) -> None:
        if self._dragging_grid:
            self._dragging_grid = False
            self._persist_state()

    # --- GEOMETRY & RENDERING ---

    def _get_resolution(self) -> tuple[int, int]:
        with suppress(Exception):
            return (int(self._res.resolution[0]), int(self._res.resolution[1]))
        return (self.winfo_screenwidth(), self.winfo_screenheight())

    def _get_cam_roi(self) -> tuple[int, int, int, int] | None:
        try:
            return (
                (int(r[0]), int(r[1]), int(r[2]), int(r[3])) if (r := getattr(self._cam, "window_roi", None)) else None
            )
        except Exception:
            return None

    def _apply_geometry(self) -> None:
        roi = self._get_cam_roi()
        rx, ry, rw, rh = roi or (0, 0, *self._get_resolution())
        self.geometry(f"{int(rw)}x{int(rh)}+{int(rx)}+{int(ry)}")
        with suppress(Exception):
            self.canvas.config(width=int(rw), height=int(rh))

    def redraw(self) -> None:
        self.canvas.delete("all")
        if not self.boards or len(n := self.boards[self.selected_board_idx].get("Nodes") or []) != NODES_LEN:
            return

        grid, acc = nodes_to_grid(n), self._accent_frame_color()
        self._apply_accent_frames()

        cs = int(self._cfg.cell_size_collapsed if self._cfg.is_collapsed else self._cfg.cell_size)
        gx, gy = (
            (int(self.grid_x_collapsed), int(self.grid_y_collapsed))
            if self._cfg.is_collapsed
            else (int(self.grid_x), int(self.grid_y))
        )

        gpx, bw = GRID * cs, self._grid_frame_thickness()
        bp = max(2, bw)

        self.canvas.create_rectangle(gx - bp, gy - bp, gx + gpx + bp, gy + gpx + bp, outline=acc, width=bw)
        self._border_rect, self._border_grab = (
            (int(gx - bp), int(gy - bp), int(gx + gpx + bp), int(gy + gpx + bp)),
            max(12, (bw * 2) + 2),
        )

        for i in range(GRID + 1):
            p = i * cs
            self.canvas.create_line(gx, gy + p, gx + gpx, gy + p, fill=FS_GRID_COLOR, width=1)
            self.canvas.create_line(gx + p, gy, gx + p, gy + gpx, fill=FS_GRID_COLOR, width=1)

        ins, ow = max(2, cs // 4), max(2, cs // 10)
        for y in range(GRID):
            for x in range(GRID):
                if grid[y][x]:
                    self.canvas.create_rectangle(
                        gx + x * cs + ins,
                        gy + y * cs + ins,
                        gx + (x + 1) * cs - ins,
                        gy + (y + 1) * cs - ins,
                        fill=TRANSPARENT_KEY,
                        outline=acc,
                        width=ow,
                    )

    # --- LIFECYCLE ---

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
            _save_overlay_settings({
                "cell_size": int(self._cfg.cell_size),
                "profile": str(self.builds[self.current_build_idx].get("profile") or "") if self.builds else "",
                "build_idx": int(self.current_build_idx),
                "board_idx": int(self.selected_board_idx),
                "grid_x": int(self.grid_x),
                "grid_y": int(self.grid_y),
                "is_collapsed": bool(self._cfg.is_collapsed),
                "cell_size_collapsed": int(self._cfg.cell_size_collapsed),
                "grid_x_collapsed": int(self.grid_x_collapsed),
                "grid_y_collapsed": int(self.grid_y_collapsed),
                "grid_locked": bool(self._cfg.grid_locked),
                "gold_frames": bool(getattr(self._cfg, "gold_frames", False)),
            })
        except Exception:
            LOGGER.debug("Failed to persist overlay state", exc_info=True)


# =============================================================================
# PUBLIC API
# =============================================================================


def run_paragon_overlay(preset_path: str | None = None, *, parent: tk.Misc | None = None) -> ParagonOverlay | None:
    try:
        if not (builds := load_builds_from_path(preset_path or (sys.argv[1] if len(sys.argv) > 1 else None))):
            LOGGER.warning("No Paragon data found in loaded profiles.")
            return None
    except Exception:
        LOGGER.exception("Failed to load Paragon preset")
        return None

    if parent is not None:
        overlay = ParagonOverlay(parent, builds, on_close=None)
        with _OVERLAY_LOCK:
            global _CURRENT_OVERLAY
            _CURRENT_OVERLAY = overlay
            _CLOSE_REQUESTED.clear()
        return overlay

    closed = threading.Event()

    def _open_overlay() -> None:
        # NOTE: This runs on the Tk UI thread.
        # If the root was not initialized, unblock the caller to avoid deadlock.
        root = _UI_ROOT
        if root is None:
            LOGGER.error("Paragon overlay: UI root not ready — aborting open")
            closed.set()
            return

        try:
            overlay = ParagonOverlay(root, builds, on_close=closed.set)
        except Exception:
            LOGGER.exception("Paragon overlay: failed to open")
            closed.set()
            return

        with _OVERLAY_LOCK:
            global _CURRENT_OVERLAY
            _CURRENT_OVERLAY = overlay
            _CLOSE_REQUESTED.clear()

    _call_on_ui_thread(_open_overlay)
    closed.wait()
    return None


def request_close(overlay: ParagonOverlay | None = None) -> None:
    with _OVERLAY_LOCK:
        if not (t := overlay or _CURRENT_OVERLAY):
            return
        _CLOSE_REQUESTED.set()
    with suppress(Exception):
        _post_to_ui_thread(lambda: t.close() if _is_alive(t) else None)


if __name__ == "__main__":
    run_paragon_overlay()
