"""Paragon overlay (tkinter).

Refactor goals (per maintainer review):
- Use tkinter Canvas (no Win32/ctypes/user32/gdi32/PIL overlay).
- Route scaling/resolution through existing Cam + ResManager.
- Keep code small and consistent with the codebase style.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import tkinter as tk
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.cam import Cam
from src.config.ui import ResManager

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

LOGGER = logging.getLogger(__name__)

GRID = 21  # 21x21 nodes


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


def load_builds_from_path(preset_path: str) -> list[dict[str, Any]]:
    p = Path(preset_path)

    msg_not_found = "Preset file/folder not found"
    if not p.exists():
        raise ValueError(msg_not_found)

    files: list[Path]
    if p.is_dir():
        files = sorted(p.glob("*.json"), key=lambda fp: fp.stat().st_mtime, reverse=True)
        msg_no_files = "Folder contains no supported preset files (*.json)"
        if not files:
            raise ValueError(msg_no_files)

        builds: list[dict[str, Any]] = []
        for fp in files:
            try:
                builds.extend(_load_builds_from_file(fp, name_tag=fp.stem, profile=fp.stem))
            except Exception:
                LOGGER.debug("Skipping invalid paragon preset JSON: %s", fp, exc_info=True)

        msg_no_builds = "No valid builds found in folder"
        if not builds:
            raise ValueError(msg_no_builds)
        return builds

    return _load_builds_from_file(p, profile=p.stem)


def _load_builds_from_file(
    preset_file: Path, *, name_tag: str | None = None, profile: str | None = None
) -> list[dict[str, Any]]:
    with preset_file.open(encoding="utf-8") as f:
        data = json.load(f)

    builds: list[dict[str, Any]] = []
    for entry in _iter_entries(data):
        base_name = entry.get("Name") or entry.get("name") or "Unknown Build"
        steps = _normalize_steps(entry.get("ParagonBoardsList", []))
        if not steps:
            continue

        # Expose steps as separate builds; final step first.
        for idx in range(len(steps) - 1, -1, -1):
            boards = steps[idx]
            step_name = base_name
            if len(steps) > 1:
                step_name = f"{base_name} - Step {idx + 1}"
            if name_tag:
                step_name = f"{step_name} [{name_tag}]"

            builds.append({"name": step_name, "boards": boards, "profile": profile})

    if not builds:
        msg_no_valid = f"No valid builds in {preset_file}"
        raise ValueError(msg_no_valid)

    return builds


def parse_rotation(rot_str: str) -> int:
    m = re.search(r"(\d+)", rot_str or "")
    deg = int(m.group(1)) if m else 0
    deg = deg % 360
    return deg if deg in (0, 90, 180, 270) else 0


def nodes_to_grid(nodes_441: list[int] | list[bool]) -> list[list[bool]]:
    # 21*21 = 441
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
    panel_w: int = 420
    poll_ms: int = 350  # watch Cam/ResManager changes without custom callbacks


class ParagonOverlay(tk.Toplevel):
    """A simple tkinter Canvas overlay for Paragon board visualization."""

    def __init__(
        self,
        parent: tk.Misc,
        builds: list[dict[str, Any]],
        *,
        cfg: OverlayConfig | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)

        self._cfg = cfg or OverlayConfig()
        self._on_close = on_close

        self.builds = builds
        self.current_build_idx = 0
        self.boards = self.builds[0]["boards"] if self.builds else []
        self.selected_board_idx = 0

        self._last_res: tuple[int, int] | None = None
        self._last_roi: tuple[int, int, int, int] | None = None

        self.title("D4LF Paragon Overlay")
        self.attributes("-topmost", True)

        # "Overlay-like" appearance (best-effort on Windows).
        self.configure(bg="#ff00ff")
        with suppress(tk.TclError):
            self.overrideredirect(True)
        with suppress(tk.TclError):
            self.wm_attributes("-transparentcolor", "#ff00ff")

        self.protocol("WM_DELETE_WINDOW", self.close)

        self._build_ui()
        self._bind_events()

        self._apply_geometry()
        self._refresh_lists()
        self.redraw()

        # Poll resolution/ROI changes (ResManager has no callback API).
        self.after(self._cfg.poll_ms, self._poll_state)

    # -------- UI layout --------
    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg="#ff00ff")
        outer.pack(fill="both", expand=True)

        # left panel
        self.left = tk.Frame(outer, width=self._cfg.panel_w, bg="#1b1b1b")
        self.left.pack(side="left", fill="y")

        header = tk.Frame(self.left, bg="#222")
        header.pack(fill="x")

        self.btn_close = tk.Button(header, text="EXIT", command=self.close)
        self.btn_close.pack(side="right", padx=6, pady=6)

        self.lbl_title = tk.Label(header, text="Paragon Overlay", fg="#eee", bg="#222")
        self.lbl_title.pack(side="left", padx=8)

        self.build_list = tk.Listbox(self.left, activestyle="none")
        self.build_list.pack(fill="x", padx=8, pady=(6, 8))

        self.board_list = tk.Listbox(self.left, activestyle="none")
        self.board_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        footer = tk.Frame(self.left, bg="#222")
        footer.pack(fill="x")
        self.lbl_hint = tk.Label(footer, text="Wheel: zoom | Drag grid: move window", fg="#cfa15b", bg="#222")
        self.lbl_hint.pack(side="left", padx=8, pady=6)

        # right: canvas
        self.right = tk.Frame(outer, bg="#000")
        self.right.pack(side="right", fill="both", expand=True)

        self.canvas = tk.Canvas(self.right, highlightthickness=0, bg="#000")
        self.canvas.pack(fill="both", expand=True)

    def _bind_events(self) -> None:
        self.build_list.bind("<<ListboxSelect>>", self._on_select_build)
        self.board_list.bind("<<ListboxSelect>>", self._on_select_board)

        # zoom
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)  # linux
        self.canvas.bind("<Button-5>", self._on_mousewheel)

        # drag window
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_move)

    # -------- polling / state --------
    def _poll_state(self) -> None:
        try:
            res = self._get_resolution()
            roi = self._get_roi()

            changed = (res != self._last_res) or (roi != self._last_roi)
            if changed:
                self._apply_geometry()
                self.redraw()

            self._last_res = res
            self._last_roi = roi
        except Exception:
            LOGGER.debug("Overlay poll failed", exc_info=True)
        finally:
            self.after(self._cfg.poll_ms, self._poll_state)

    # -------- handlers --------
    def _on_select_build(self, _: Any) -> None:
        sel = self._get_listbox_index(self.build_list)
        if sel is None:
            return
        self.current_build_idx = sel
        self.boards = self.builds[sel]["boards"]
        self.selected_board_idx = 0
        self._refresh_lists()
        self.redraw()

    def _on_select_board(self, _: Any) -> None:
        sel = self._get_listbox_index(self.board_list)
        if sel is None:
            return
        self.selected_board_idx = sel
        self.redraw()

    def _on_mousewheel(self, e: tk.Event) -> None:
        delta = 0
        if getattr(e, "delta", 0):
            delta = 1 if e.delta > 0 else -1
        elif getattr(e, "num", 0) in (4, 5):
            delta = 1 if e.num == 4 else -1

        if not delta:
            return

        new_size = max(10, min(80, self._cfg.cell_size + (2 * delta)))
        if new_size != self._cfg.cell_size:
            self._cfg.cell_size = new_size
            self.redraw()

    def _on_drag_start(self, e: tk.Event) -> None:
        self._drag_start_xy = (e.x_root, e.y_root)
        self._drag_start_geo = (self.winfo_x(), self.winfo_y())

    def _on_drag_move(self, e: tk.Event) -> None:
        sx, sy = self._drag_start_xy
        gx, gy = self._drag_start_geo
        dx = e.x_root - sx
        dy = e.y_root - sy
        self.geometry(f"+{gx + dx}+{gy + dy}")

    # -------- helpers --------
    @staticmethod
    def _get_listbox_index(lb: tk.Listbox) -> int | None:
        cur = lb.curselection()
        return int(cur[0]) if cur else None

    def _get_resolution(self) -> tuple[int, int]:
        # ResManager.resolution -> (w, h) based on active res key.
        try:
            w, h = ResManager().resolution[:2]
            return (int(w), int(h))
        except Exception:
            return (self.winfo_screenwidth(), self.winfo_screenheight())

    def _get_roi(self) -> tuple[int, int, int, int] | None:
        try:
            roi = Cam().window_roi
        except Exception:
            return None
        if not roi or len(roi) < 4:
            return None
        x, y, w, h = roi[:4]
        return (int(x), int(y), int(w), int(h))

    def _apply_geometry(self) -> None:
        # Prefer ROI (game window) size/position if present; else use screen resolution.
        res_w, res_h = self._get_resolution()
        roi = self._get_roi()

        if roi is not None:
            roi_x, roi_y, roi_w, roi_h = roi
            # Attach overlay near the game window top-left; keep a small offset.
            x0, y0 = roi_x + 20, roi_y + 20
            available_w = max(800, roi_w - 40)
            available_h = max(600, roi_h - 40)
        else:
            x0, y0 = 20, 20
            available_w = res_w
            available_h = res_h

        grid_w = min(760, max(480, available_w - self._cfg.panel_w - 80))
        grid_h = min(760, max(480, available_h - 120))
        total_w = self._cfg.panel_w + grid_w
        total_h = grid_h

        self.geometry(f"{total_w}x{total_h}+{x0}+{y0}")
        self.canvas.config(width=grid_w, height=grid_h)

    def _refresh_lists(self) -> None:
        self.build_list.delete(0, tk.END)
        for b in self.builds:
            self.build_list.insert(tk.END, b.get("name", "Unknown Build"))
        if self.builds:
            self.build_list.selection_set(self.current_build_idx)

        self.board_list.delete(0, tk.END)
        for bd in self.boards or []:
            name = bd.get("Name", "?")
            rot = bd.get("Rotation", "0")
            glyph = bd.get("Glyph")
            label = f"{name} ({rot})"
            if glyph:
                label += f" ({glyph})"
            self.board_list.insert(tk.END, label)
        if self.boards:
            self.board_list.selection_set(self.selected_board_idx)

        cur_name = self.builds[self.current_build_idx]["name"] if self.builds else "Paragon Overlay"
        self.lbl_title.config(text=cur_name)

    # -------- drawing --------
    def redraw(self) -> None:
        self.canvas.delete("all")
        if not self.boards:
            self.canvas.create_text(20, 20, anchor="nw", fill="#fff", text="No boards loaded")
            return

        board = self.boards[self.selected_board_idx]
        nodes = board.get("Nodes") or []
        if len(nodes) != GRID * GRID:
            self.canvas.create_text(20, 20, anchor="nw", fill="#fff", text="Invalid board node data")
            return

        rot = parse_rotation(board.get("Rotation", "0°"))
        grid = rotate_grid(nodes_to_grid(nodes), rot)

        cs = self._cfg.cell_size
        pad = 16
        gx0, gy0 = pad, pad
        grid_px = GRID * cs

        # background frame
        self.canvas.create_rectangle(gx0 - 6, gy0 - 6, gx0 + grid_px + 6, gy0 + grid_px + 6, outline="#cfa15b", width=3)

        # grid lines
        for i in range(GRID + 1):
            p = i * cs
            self.canvas.create_line(gx0, gy0 + p, gx0 + grid_px, gy0 + p, fill="#444", width=1)
            self.canvas.create_line(gx0 + p, gy0, gx0 + p, gy0 + grid_px, fill="#444", width=1)

        # paths
        path_w = max(2, cs // 6)
        half = cs // 2
        for y in range(GRID):
            for x in range(GRID):
                if not grid[y][x]:
                    continue
                cx = gx0 + x * cs + half
                cy = gy0 + y * cs + half
                if x + 1 < GRID and grid[y][x + 1]:
                    nx = gx0 + (x + 1) * cs + half
                    self.canvas.create_line(cx, cy, nx, cy, fill="#22aa44", width=path_w)
                if y + 1 < GRID and grid[y + 1][x]:
                    ny = gy0 + (y + 1) * cs + half
                    self.canvas.create_line(cx, cy, cx, ny, fill="#22aa44", width=path_w)

        # active nodes
        inset = max(3, cs // 4)
        for y in range(GRID):
            for x in range(GRID):
                if not grid[y][x]:
                    continue
                x1 = gx0 + x * cs + inset
                y1 = gy0 + y * cs + inset
                x2 = gx0 + (x + 1) * cs - inset
                y2 = gy0 + (y + 1) * cs - inset
                self.canvas.create_rectangle(x1, y1, x2, y2, fill="#18dd44", outline="#bbffbb", width=1)

    # -------- lifecycle --------
    def close(self) -> None:
        try:
            self.destroy()
        finally:
            if self._on_close:
                self._on_close()


# ----------------------------
# Public API (used by app)
# ----------------------------
def run_paragon_overlay(preset_path: str | None = None, *, parent: tk.Misc | None = None) -> ParagonOverlay | None:
    """Start overlay in-process. If parent is None, a Tk root is created."""
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
    if owns_root:
        parent.mainloop()
    return overlay


def request_close(overlay: ParagonOverlay | None) -> None:
    """Best-effort close from elsewhere."""
    if overlay is None:
        return
    with suppress(Exception):
        overlay.after(0, overlay.close)


if __name__ == "__main__":
    run_paragon_overlay()
