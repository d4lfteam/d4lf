"""Paragon overlay (tkinter)."""

from __future__ import annotations

import configparser
import json
import logging
import re
import sys
import threading
import tkinter as tk
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.cam import Cam
from src.config.ui import ResManager

try:
    from ruamel.yaml import YAML as RUAMEL_YAML
except ImportError:  # pragma: no cover
    RUAMEL_YAML = None

try:
    import yaml as PyYAML
except ImportError:  # pragma: no cover
    PyYAML = None

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

GRID = 21  # 21x21 nodes
NODES_LEN = GRID * GRID


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


def _load_yaml_file(path: Path) -> dict[str, Any] | None:
    try:
        if RUAMEL_YAML is not None:
            y = RUAMEL_YAML(typ="rt")
            with path.open("r", encoding="utf-8") as f:
                loaded = y.load(f) or {}
            return loaded if isinstance(loaded, dict) else None
        if PyYAML is not None:
            with path.open("r", encoding="utf-8") as f:
                loaded = PyYAML.safe_load(f) or {}
            return loaded if isinstance(loaded, dict) else None
    except Exception:
        LOGGER.debug("Failed reading YAML: %s", path, exc_info=True)
        return None

    LOGGER.error("No YAML library available (ruamel.yaml or PyYAML)")
    return None


def _extract_paragon_payloads_from_profile_yaml(profile_yaml: dict[str, Any]) -> Iterable[dict[str, Any]]:
    paragon = profile_yaml.get("Paragon")
    if isinstance(paragon, dict):
        yield paragon
        return
    if isinstance(paragon, list):
        for it in paragon:
            if isinstance(it, dict):
                yield it


def load_builds_from_path(preset_path: str) -> list[dict[str, Any]]:
    p = Path(preset_path)

    if not p.exists():
        msg = "Preset file/folder not found"
        raise ValueError(msg)

    builds: list[dict[str, Any]] = []

    if p.is_file():
        suffix = p.suffix.lower()
        if suffix == ".json":
            builds.extend(_load_builds_from_json_file(p, profile=p.stem))
        elif suffix in (".yaml", ".yml"):
            builds.extend(_load_builds_from_profile_yaml_file(p, profile=p.stem))
        else:
            msg = "Unsupported preset file type"
            raise ValueError(msg)

        if not builds:
            msg = "No valid builds found"
            raise ValueError(msg)
        return builds

    # Directory mode:
    json_files = sorted(p.glob("*.json"), key=lambda fp: fp.stat().st_mtime, reverse=True)
    if json_files:
        for fp in json_files:
            try:
                builds.extend(_load_builds_from_json_file(fp, name_tag=fp.stem, profile=fp.stem))
            except Exception:
                LOGGER.debug("Skipping invalid paragon preset JSON: %s", fp, exc_info=True)

    yaml_dirs: list[Path] = []
    if (p / "profiles").is_dir():
        yaml_dirs.append(p / "profiles")
    if (p.parent / "profiles").is_dir():
        yaml_dirs.append(p.parent / "profiles")
    yaml_dirs.append(p)

    seen: set[Path] = set()
    for yd in yaml_dirs:
        for fp in sorted(yd.glob("*.ya*"), key=lambda x: x.stat().st_mtime, reverse=True):
            if fp in seen:
                continue
            seen.add(fp)
            try:
                builds.extend(_load_builds_from_profile_yaml_file(fp, profile=fp.stem))
            except Exception:
                LOGGER.debug("Skipping invalid profile YAML: %s", fp, exc_info=True)

    if not builds:
        msg = "No valid builds found in folder"
        raise ValueError(msg)
    return builds


def _load_builds_from_json_file(
    preset_file: Path, name_tag: str | None = None, profile: str | None = None
) -> list[dict[str, Any]]:
    with preset_file.open(encoding="utf-8") as f:
        data = json.load(f)

    builds: list[dict[str, Any]] = []
    for entry in _iter_entries(data):
        builds.extend(_builds_from_paragon_entry(entry, name_tag=name_tag, profile=profile))
    if not builds:
        msg = "No valid builds in JSON"
        raise ValueError(msg)
    return builds


def _load_builds_from_profile_yaml_file(profile_file: Path, profile: str | None = None) -> list[dict[str, Any]]:
    loaded = _load_yaml_file(profile_file)
    if not loaded:
        msg = "Invalid or empty profile YAML"
        raise ValueError(msg)

    builds: list[dict[str, Any]] = []
    for payload in _extract_paragon_payloads_from_profile_yaml(loaded):
        builds.extend(_builds_from_paragon_entry(payload, name_tag=profile_file.stem, profile=profile))
    if not builds:
        msg = "No Paragon payload found in profile YAML"
        raise ValueError(msg)
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
    cell_size: int = 24
    panel_w: int = 380
    poll_ms: int = 500
    window_alpha: float = 0.86


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

        saved_cell = self._settings.get("cell_size")
        if isinstance(saved_cell, int):
            self._cfg.cell_size = _clamp_int(saved_cell, 10, 80, self._cfg.cell_size)

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

        # Grid position is independent from the left UI and persisted.
        self.grid_x = self._settings.get("grid_x")
        self.grid_y = self._settings.get("grid_y")
        if not isinstance(self.grid_x, int):
            self.grid_x = self._cfg.panel_w + 24
        if not isinstance(self.grid_y, int):
            self.grid_y = 24

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
        self.after(self._cfg.poll_ms, self._poll_window_state)
        self.after(50, self._poll_close_request)

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

        # Title card (longer)
        self.card_title = tk.Frame(self.left, bg=CARD_BG, height=120)
        self.card_title.pack(fill="x", padx=10, pady=(10, 14))
        self.card_title.pack_propagate(False)

        title_row = tk.Frame(self.card_title, bg=CARD_BG)
        title_row.pack(fill="both", expand=True, padx=12)

        self.lbl_title = tk.Label(
            title_row,
            text="",
            fg=TEXT,
            bg=CARD_BG,
            font=("Segoe UI", 14, "bold"),
            anchor="w",
            wraplength=max(200, self._cfg.panel_w - 90),
            justify="left",
        )
        self.lbl_title.pack(side="left", fill="x", expand=True)

        self.btn_build_menu = tk.Button(
            title_row,
            text="▼",
            command=self._show_build_menu,
            padx=6,
            pady=0,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=TEXT,
            bd=0,
            highlightthickness=0,
            font=("Segoe UI", 12, "bold"),
        )
        self.btn_build_menu.pack(side="left", padx=(8, 0))

        # Scrollable board cards area (no solid background block)
        self.boards_canvas = tk.Canvas(self.left, bg=TRANSPARENT_KEY, highlightthickness=0)
        self.boards_canvas.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        self.board_container = tk.Frame(self.boards_canvas, bg=TRANSPARENT_KEY)
        self._boards_window_id = self.boards_canvas.create_window((0, 0), window=self.board_container, anchor="nw")

        def _on_container_configure(_: tk.Event) -> None:
            self.boards_canvas.configure(scrollregion=self.boards_canvas.bbox("all"))

        def _on_canvas_configure(e: tk.Event) -> None:
            # Keep cards full width of the visible canvas
            self.boards_canvas.itemconfigure(self._boards_window_id, width=int(e.width))

        self.board_container.bind("<Configure>", _on_container_configure)
        self.boards_canvas.bind("<Configure>", _on_canvas_configure)

    def _bind_events(self) -> None:
        # Grid zoom
        self.canvas.bind("<MouseWheel>", self._on_grid_mousewheel)
        self.canvas.bind("<Button-4>", self._on_grid_mousewheel)
        self.canvas.bind("<Button-5>", self._on_grid_mousewheel)

        # Board list scroll
        self.boards_canvas.bind("<MouseWheel>", self._on_boards_mousewheel)
        self.boards_canvas.bind("<Button-4>", self._on_boards_mousewheel)
        self.boards_canvas.bind("<Button-5>", self._on_boards_mousewheel)

        # Drag the grid by grabbing the gold border.
        self.canvas.bind("<ButtonPress-1>", self._on_grid_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_grid_drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_grid_drag_end)

        # Drag the whole overlay window via the title card.
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

    def _show_build_menu(self) -> None:
        if not self.builds:
            return

        m = tk.Menu(self, tearoff=0, bg=CARD_BG, fg=TEXT, activebackground=SELECT_BG, activeforeground=GOLD, bd=0)

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
                    self, tearoff=0, bg=CARD_BG, fg=TEXT, activebackground=SELECT_BG, activeforeground=GOLD, bd=0
                )
                for i, b in groups[prof]:
                    _add_item(sm, i, b)
                m.add_cascade(label=prof, menu=sm)
        else:
            for i, b in enumerate(self.builds):
                _add_item(m, i, b)

        try:
            x = self.btn_build_menu.winfo_rootx()
            y = self.btn_build_menu.winfo_rooty() + self.btn_build_menu.winfo_height()
            m.tk_popup(x, y)
        finally:
            with suppress(Exception):
                m.grab_release()

    # -------- board cards --------
    def _select_board_card(self, idx: int) -> None:
        self.selected_board_idx = _clamp_int(idx, 0, max(0, len(self.boards) - 1), 0)
        self._refresh_lists()
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
            name = bd.get("Name", "?")
            rot = bd.get("Rotation", "0")
            glyph = bd.get("Glyph")

            text = f"{name} ({rot})"
            if glyph:
                text += f" • {glyph}"

            selected = idx == self.selected_board_idx
            bg = SELECT_BG if selected else CARD_BG
            fg = GOLD if selected else TEXT

            card = tk.Frame(self.board_container, bg=bg, height=76)
            card.pack(fill="x", pady=8)
            card.pack_propagate(False)

            lbl = tk.Label(
                card,
                text=text,
                fg=fg,
                bg=bg,
                anchor="w",
                padx=14,
                pady=16,
                font=("Segoe UI", 11, "bold"),
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

    def _on_grid_drag_start(self, e: tk.Event) -> None:
        if not self._is_on_gold_border(int(e.x), int(e.y)):
            self._dragging_grid = False
            return
        self._dragging_grid = True
        self._drag_start_xy = (int(e.x_root), int(e.y_root))
        self._drag_start_grid = (int(self.grid_x), int(self.grid_y))

    def _on_grid_drag_move(self, e: tk.Event) -> None:
        if not self._dragging_grid:
            return
        sx, sy = self._drag_start_xy
        gx, gy = self._drag_start_grid
        dx = int(e.x_root) - sx
        dy = int(e.y_root) - sy
        self.grid_x = gx + dx
        self.grid_y = gy + dy
        self.redraw()

    def _on_grid_drag_end(self, _: tk.Event) -> None:
        if not self._dragging_grid:
            return
        self._dragging_grid = False
        self._persist_state()

    def _on_window_drag_start(self, e: tk.Event) -> None:
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
    def _draw_grid_hints(self, gx0: int, gy0: int, *, border_pad: int) -> None:
        """Draw small help text near the paragon grid (directly on the canvas)."""
        hint = (
            "Hover over the golden frame; mouse wheel up/down = zoom +/-\n"
            "Hold left click on the golden frame to drag/drop the grid"
        )

        # Prefer above the grid. If there's not enough space, place inside the top-left.
        x = int(gx0 - border_pad + 4)
        y_above = int(gy0 - border_pad - 8)

        font_size = max(9, min(12, int(self._cfg.cell_size * 0.45)))
        text_id = self.canvas.create_text(
            x, y_above, text=hint, fill=MUTED, font=("Segoe UI", font_size), anchor="sw", justify="left"
        )

        bbox = self.canvas.bbox(text_id) or (x, y_above, x + 10, y_above + 10)
        if bbox[1] < 8:
            # Move inside the frame if it would be clipped.
            self.canvas.delete(text_id)
            y_inside = int(gy0 - border_pad + 10)
            text_id = self.canvas.create_text(
                x, y_inside, text=hint, fill=MUTED, font=("Segoe UI", font_size), anchor="nw", justify="left"
            )
            bbox = self.canvas.bbox(text_id) or (x, y_inside, x + 10, y_inside + 10)

        pad_x, pad_y = 8, 6
        rect_id = self.canvas.create_rectangle(
            bbox[0] - pad_x, bbox[1] - pad_y, bbox[2] + pad_x, bbox[3] + pad_y, fill=CARD_BG, outline=""
        )
        self.canvas.tag_raise(text_id, rect_id)

    def redraw(self) -> None:
        self.canvas.delete("all")
        if not self.boards:
            return

        board = self.boards[self.selected_board_idx]
        nodes = board.get("Nodes") or []
        if len(nodes) != NODES_LEN:
            return

        rot = parse_rotation(board.get("Rotation", "0°"))
        grid = rotate_grid(nodes_to_grid(nodes), rot)

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

        self._draw_grid_hints(gx0, gy0, border_pad=border_pad)

        # Grid lines
        for i in range(GRID + 1):
            p = i * cs
            self.canvas.create_line(gx0, gy0 + p, gx0 + grid_px, gy0 + p, fill="#3f3f3f", width=1)
            self.canvas.create_line(gx0 + p, gy0, gx0 + p, gy0 + grid_px, fill="#3f3f3f", width=1)

        # Nodes
        inset = max(2, cs // 4)
        outline_w = max(2, cs // 10)
        for y in range(GRID):
            for x in range(GRID):
                if not grid[y][x]:
                    continue
                x1 = gx0 + x * cs + inset
                y1 = gy0 + y * cs + inset
                x2 = gx0 + (x + 1) * cs - inset
                y2 = gy0 + (y + 1) * cs - inset
                self.canvas.create_rectangle(x1, y1, x2, y2, fill="", outline="#18dd44", width=outline_w)

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
            })
        except Exception:
            LOGGER.debug("Failed to persist overlay state", exc_info=True)


# ----------------------------
# Public API (used by app)
# ----------------------------
def run_paragon_overlay(preset_path: str | None = None, *, parent: tk.Misc | None = None) -> ParagonOverlay | None:
    """Start overlay in-process."""
    preset = preset_path or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not preset:
        LOGGER.error("No preset path provided")
        return None

    try:
        builds = load_builds_from_path(preset)
    except Exception:
        LOGGER.exception("Failed to load Paragon preset(s): %s", preset)
        return None

    owns_root = False
    if parent is None:
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
