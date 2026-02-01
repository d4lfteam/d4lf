# Integrated into D4LF as src.paragon_overlay
# Original file: d4.py (Win32 layered window Paragon overlay)
# Entry: run_paragon_overlay(preset_path)

# d4_paragon_overlay_v14_fix_button.py
#
# Features:
#   - FIX: Start/Stop Button is now ALWAYS visible (drawn on top of header)
#   - EXIT BUTTON (Right side of hint bar)
#   - MENU POSITION: Top-Left (0,0)
#   - THICK GOLD FRAME
#   - ALWAYS ON TOP
#   - 64-Bit Safe
#
# Controls:
#   [Top-Left Button]: Toggle Start/Stop
#   [Red 'EXIT' Button]: Close App
#   [Build Header]: Switch Build
#   [Scroll Wheel]: Zoom
#   [Drag]: Move

import contextlib
import ctypes
import ctypes.wintypes as wt
import json
import logging
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# --- HARDENED WIN32 DEFINITIONS (64-BIT SAFE) ---
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Explicit types
HANDLE = ctypes.c_void_p
HWND = ctypes.c_void_p
HDC = ctypes.c_void_p
HBITMAP = ctypes.c_void_p
HGDIOBJ = ctypes.c_void_p
HICON = ctypes.c_void_p
HCURSOR = ctypes.c_void_p
HBRUSH = ctypes.c_void_p
HMENU = ctypes.c_void_p
HINSTANCE = ctypes.c_void_p
LPVOID = ctypes.c_void_p
LPARAM = ctypes.c_longlong
WPARAM = ctypes.c_ulonglong
LRESULT = ctypes.c_longlong

WNDPROCTYPE = ctypes.WINFUNCTYPE(LRESULT, HWND, wt.UINT, WPARAM, LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wt.UINT),
        ("lpfnWndProc", WNDPROCTYPE),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR),
    ]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", wt.BYTE),
        ("BlendFlags", wt.BYTE),
        ("SourceConstantAlpha", wt.BYTE),
        ("AlphaFormat", wt.BYTE),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD),
        ("biWidth", wt.LONG),
        ("biHeight", wt.LONG),
        ("biPlanes", wt.WORD),
        ("biBitCount", wt.WORD),
        ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD),
        ("biXPelsPerMeter", wt.LONG),
        ("biYPelsPerMeter", wt.LONG),
        ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", ctypes.c_ulong * 3)]


# --- API Signatures ---
kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
kernel32.GetModuleHandleW.restype = HINSTANCE
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wt.ATOM
user32.CreateWindowExW.argtypes = [
    wt.DWORD,
    wt.LPCWSTR,
    wt.LPCWSTR,
    wt.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    HWND,
    HMENU,
    HINSTANCE,
    LPVOID,
]
user32.CreateWindowExW.restype = HWND
user32.DefWindowProcW.argtypes = [HWND, wt.UINT, WPARAM, LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.UpdateLayeredWindow.argtypes = [
    HWND,
    HDC,
    ctypes.POINTER(wt.POINT),
    ctypes.POINTER(wt.SIZE),
    HDC,
    ctypes.POINTER(wt.POINT),
    wt.COLORREF,
    ctypes.POINTER(BLENDFUNCTION),
    wt.DWORD,
]
user32.UpdateLayeredWindow.restype = wt.BOOL
user32.GetDC.argtypes = [HWND]
user32.GetDC.restype = HDC
user32.ReleaseDC.argtypes = [HWND, HDC]
user32.ReleaseDC.restype = ctypes.c_int
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None
user32.SetFocus.argtypes = [HWND]
user32.SetFocus.restype = HWND
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = wt.SHORT
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.LoadCursorW.argtypes = [HINSTANCE, wt.LPCWSTR]
user32.LoadCursorW.restype = HCURSOR
user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), HWND, wt.UINT, wt.UINT]
user32.GetMessageW.restype = wt.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wt.MSG)]
user32.TranslateMessage.restype = wt.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wt.MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.SetCapture.argtypes = [HWND]
user32.SetCapture.restype = HWND
user32.ReleaseCapture.argtypes = []
user32.ReleaseCapture.restype = wt.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
user32.GetCursorPos.restype = wt.BOOL
user32.SetCursor.argtypes = [HCURSOR]
user32.SetCursor.restype = HCURSOR
user32.SetWindowPos.argtypes = [HWND, HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
user32.SetWindowPos.restype = wt.BOOL

gdi32.CreateCompatibleDC.argtypes = [HDC]
gdi32.CreateCompatibleDC.restype = HDC
gdi32.SelectObject.argtypes = [HDC, HGDIOBJ]
gdi32.SelectObject.restype = HGDIOBJ
gdi32.DeleteDC.argtypes = [HDC]
gdi32.DeleteDC.restype = wt.BOOL
gdi32.DeleteObject.argtypes = [HGDIOBJ]
gdi32.DeleteObject.restype = wt.BOOL
gdi32.CreateDIBSection.argtypes = [
    HDC,
    ctypes.POINTER(BITMAPINFO),
    wt.UINT,
    ctypes.POINTER(ctypes.c_void_p),
    HANDLE,
    wt.DWORD,
]
gdi32.CreateDIBSection.restype = HBITMAP

# --- Constants ---
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_EX_TOPMOST = 0x00000008
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
BI_RGB = 0
WM_DESTROY = 0x0002
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEMOVE = 0x0200
WM_MOUSEWHEEL = 0x020A
WM_KEYDOWN = 0x0100
WM_NCHITTEST = 0x0084
HTCLIENT = 1
VK_LEFT, VK_UP, VK_RIGHT, VK_DOWN = 0x25, 0x26, 0x27, 0x28
VK_SHIFT = 0x10
IDC_ARROW = 32512
IDC_SIZEALL = 32646

HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

# --- Logic & Data ---
GRID = 21
PANEL_W = 600
ITEM_H = 34
HEADER_H = 80

# Colors
C_GRID_LINE = (80, 80, 80, 60)
C_GRID_FRAME = (217, 143, 57, 240)
C_GRID_FRAME_BG = (0, 0, 0, 150)
C_NODE_ACTIVE = (0, 255, 60, 220)
C_NODE_PATH = (0, 200, 50, 160)
C_ACTION_BG = (50, 60, 80, 220)
C_ITEM_BG = (30, 30, 30, 200)
C_ITEM_BORDER = (80, 80, 80, 255)
C_TEXT = (240, 240, 240, 255)
C_TEXT_DIM = (180, 180, 180, 255)
C_GOLD = (217, 143, 57, 255)

LOGGER = logging.getLogger(__name__)


def _msgbox(title: str, text: str) -> None:
    """Show a Windows message box. Safe no-op on non-Windows."""
    with contextlib.suppress(Exception):
        if sys.platform == "win32":
            user32.MessageBoxW(None, str(text), str(title), 0)


def get_xy(lparam):
    return (lparam & 0xFFFF), ((lparam >> 16) & 0xFFFF)


def parse_rotation(rot_str: str) -> int:
    m = re.search(r"(\d+)", rot_str or "")
    deg = int(m.group(1)) if m else 0
    return deg % 360 if deg % 360 in (0, 90, 180, 270) else 0


def nodes_to_grid(nodes_441):
    return [[bool(nodes_441[y * GRID + x]) for x in range(GRID)] for y in range(GRID)]


def rotate_grid(grid, deg: int):
    if deg == 90:
        return [list(reversed(col)) for col in zip(*grid, strict=True)]
    if deg == 180:
        return [list(reversed(r)) for r in reversed(grid)]
    if deg == 270:
        return [list(col) for col in reversed(list(zip(*grid, strict=True)))]
    return grid


def _iter_entries(data):
    """Yield build-like dicts from JSON that can be either a list[dict] or a dict."""
    if isinstance(data, dict):
        yield data
    elif isinstance(data, list):
        for it in data:
            if isinstance(it, dict):
                yield it


def _normalize_steps(raw_list):
    """Normalize ParagonBoardsList to a list of steps, each step being a list[board]."""
    if not isinstance(raw_list, list) or not raw_list:
        return []
    # If first element is a list, assume list-of-steps.
    if isinstance(raw_list[0], list):
        return [step for step in raw_list if isinstance(step, list) and step]
    # Otherwise assume a single step list-of-boards.
    return [raw_list]


def _load_builds_from_file(preset_file: str, name_tag: str | None = None):
    """Load one JSON file and return a list of builds in overlay format: {name, boards}.

    Supports:
      - D4LF paragon exports (JSON list with single entry)
      - AffixPresets-v2 style (JSON list with many entries)
      - A single dict payload
    Also expands multi-step ParagonBoardsList into multiple selectable builds.
    """
    with Path(preset_file).open(encoding="utf-8") as f:
        data = json.load(f)

    builds = []
    for entry in _iter_entries(data):
        base_name = entry.get("Name") or entry.get("name") or "Unknown Build"
        steps = _normalize_steps(entry.get("ParagonBoardsList", []))
        if not steps:
            continue

        # If there are multiple steps, expose them as separate selectable builds.
        # For planners that provide many incremental steps (e.g., Maxroll), it's more useful to start on the FINAL step.
        for idx in range(len(steps) - 1, -1, -1):
            boards = steps[idx]
            step_no = idx + 1
            step_name = base_name
            if len(steps) > 1:
                step_name = f"{base_name} - Step {step_no}"
            if name_tag:
                step_name = f"{step_name} [{name_tag}]"
            builds.append({"name": step_name, "boards": boards})

    if not builds:
        msg = f"No valid builds in {preset_file}"
        raise ValueError(msg)

    return builds


def load_builds_from_path(preset_path: str):
    """Load builds from a JSON file OR from a folder containing multiple *.json files."""
    p = Path(preset_path)
    if p.is_dir():
        files = sorted(p.glob("*.json"), key=lambda fp: fp.stat().st_mtime, reverse=True)
        if not files:
            msg = "Folder contains no .json files"
            raise ValueError(msg)
        multi = len(files) > 1
        builds = []
        for fp in files:
            try:
                builds.extend(_load_builds_from_file(str(fp), name_tag=(fp.stem if multi else None)))
            except json.JSONDecodeError, OSError, KeyError, TypeError, ValueError:
                LOGGER.debug("Skipping invalid paragon preset JSON: %s", fp, exc_info=True)
        if not builds:
            msg = "No valid builds found in folder"
            raise ValueError(msg)
        return builds

    if not p.exists():
        msg = "Preset file not found"
        raise ValueError(msg)

    return _load_builds_from_file(str(p))


def get_font(size: int = 14, bold: bool = False):
    font_name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(font_name, size)
    except OSError:
        return ImageFont.load_default()


FONT_HEADER = get_font(16, bold=True)
FONT_ITEM = get_font(13, bold=True)
FONT_SMALL = get_font(11, bold=False)


def render_grid_window(board, cell_size):
    rot_deg = parse_rotation(board.get("Rotation", "0°"))
    grid = rotate_grid(nodes_to_grid(board["Nodes"]), rot_deg)
    grid_px = GRID * cell_size

    img = Image.new("RGBA", (grid_px + 30, grid_px + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    gx0, gy0 = 15, 15
    half_cell = cell_size // 2

    # 1. Background Grid
    for i in range(GRID + 1):
        p = i * cell_size
        d.line([(gx0, gy0 + p), (gx0 + grid_px, gy0 + p)], fill=C_GRID_LINE, width=1)
        d.line([(gx0 + p, gy0), (gx0 + p, gy0 + grid_px)], fill=C_GRID_LINE, width=1)

    # 2. Draw Paths
    path_width = max(2, cell_size // 6)
    for y in range(GRID):
        for x in range(GRID):
            if grid[y][x]:
                cx, cy = gx0 + x * cell_size + half_cell, gy0 + y * cell_size + half_cell
                if x + 1 < GRID and grid[y][x + 1]:
                    nx, ny = gx0 + (x + 1) * cell_size + half_cell, cy
                    d.line([(cx, cy), (nx, ny)], fill=C_NODE_PATH, width=path_width)
                if y + 1 < GRID and grid[y + 1][x]:
                    nx, ny = cx, gy0 + (y + 1) * cell_size + half_cell
                    d.line([(cx, cy), (nx, ny)], fill=C_NODE_PATH, width=path_width)

    # 3. Draw Nodes
    inset = max(3, cell_size // 4)
    for y in range(GRID):
        for x in range(GRID):
            if grid[y][x]:
                px, py = gx0 + x * cell_size, gy0 + y * cell_size
                d.rectangle(
                    (px + inset, py + inset, px + cell_size - inset, py + cell_size - inset),
                    fill=C_NODE_ACTIVE,
                    outline=None,
                )
                d.rectangle(
                    (px + inset, py + inset, px + cell_size - inset, py + cell_size - inset),
                    outline=(200, 255, 200, 100),
                    width=1,
                )

    # 4. THICK Outer Frame
    frame_thick = 5
    d.rectangle(
        (gx0 - 1, gy0 - 1, gx0 + grid_px + 1, gy0 + grid_px + 1), outline=C_GRID_FRAME_BG, width=frame_thick + 2
    )
    d.rectangle((gx0, gy0, gx0 + grid_px, gy0 + grid_px), outline=C_GRID_FRAME, width=frame_thick)

    return img


def render_list_window(state):
    minimized = state.minimized
    selecting = state.selecting_build

    # 1. PREPARE TOGGLE BUTTON
    btn_rect = [2, 2, 26, 26]
    if minimized:
        fill_col = (200, 50, 50)  # Red
        symbol = "\u2716"  # X
        txt_offset = (6, 5)
    else:
        fill_col = (50, 200, 50)  # Green
        symbol = "\u2714"  # Check
        txt_offset = (6, 5)

    # 2. IF MINIMIZED -> DRAW ONLY BUTTON AND RETURN
    if minimized:
        img = Image.new("RGBA", (PANEL_W, 30), (0, 0, 0, 1))
        d = ImageDraw.Draw(img)
        d.rectangle(btn_rect, fill=fill_col, outline=(200, 200, 200))
        d.text(txt_offset, symbol, fill=(255, 255, 255, 255), font=FONT_ITEM)
        return img

    # 3. IF OPEN -> DRAW CONTENT
    if selecting:
        data, title = state.builds, "Select Build (Click to cancel)"
        active_idx = state.current_build_idx
    else:
        data, title = state.boards, state.build_name + " \u25bc"
        active_idx = state.selected

    rows = len(data)
    total_h = HEADER_H + (rows * (ITEM_H + 4)) + 10

    img = Image.new("RGBA", (PANEL_W, total_h), (0, 0, 0, 1))
    d = ImageDraw.Draw(img)

    # Header Background
    d.rectangle((0, 0, PANEL_W, HEADER_H), fill=C_ACTION_BG if selecting else C_ITEM_BG)
    d.text((35, 10), title, fill=C_TEXT, font=FONT_HEADER)

    # Hint Box
    d.rectangle((0, 50, PANEL_W - 5, 85), fill=C_ITEM_BG, outline=C_ITEM_BORDER, width=1)
    hint = f"Found {len(data)} builds" if selecting else "click on golden frame= Zoom: Mousewheel | Move: Drag Grid"
    d.text((12, 58), hint, fill=C_GOLD, font=FONT_SMALL)

    # EXIT BUTTON (Right side)
    exit_rect = [PANEL_W - 35, 55, PANEL_W - 10, 80]
    d.rectangle(exit_rect, fill=(180, 0, 0), outline=(200, 200, 200))
    d.text((PANEL_W - 30, 59), "EXIT", fill=(255, 255, 255), font=get_font(9, True))

    d.line([(0, HEADER_H), (PANEL_W, HEADER_H)], fill=C_GOLD, width=1)

    # List Items
    y_start = HEADER_H + 10
    for i, item in enumerate(data):
        label = item["name"] if selecting else f"{item.get('Name', '?')} ({item.get('Rotation', '0')})"
        if not selecting and item.get("Glyph"):
            label += f" ({item.get('Glyph')})"

        y = y_start + i * (ITEM_H + 4)
        bg, border, txt = C_ITEM_BG, C_ITEM_BORDER, C_TEXT_DIM

        if i == active_idx:
            bg, border, txt = (40, 35, 20, 220), C_GOLD, C_TEXT
        elif i == state.hover:
            border, txt = (150, 150, 150, 255), C_TEXT

        d.rectangle((0, y, PANEL_W - 5, y + ITEM_H), fill=bg, outline=border, width=1)
        d.text((10, y + (ITEM_H - 13) // 2 - 2), label, fill=txt, font=FONT_ITEM)

    # 4. DRAW TOGGLE BUTTON LAST (So it sits ON TOP of Header)
    d.rectangle(btn_rect, fill=fill_col, outline=(200, 200, 200))
    d.text(txt_offset, symbol, fill=(255, 255, 255, 255), font=FONT_ITEM)

    return img


def pil_to_hbitmap(pil_img):
    img = pil_img.convert("RGBA")
    w, h = img.size
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth, bmi.bmiHeader.biHeight = w, -h
    bmi.bmiHeader.biPlanes, bmi.bmiHeader.biBitCount = 1, 32
    bmi.bmiHeader.biCompression = BI_RGB
    bits = ctypes.c_void_p()
    hdc_screen = user32.GetDC(None)
    hbmp = gdi32.CreateDIBSection(hdc_screen, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    user32.ReleaseDC(None, hdc_screen)
    ctypes.memmove(bits, img.tobytes("raw", "BGRA"), w * h * 4)
    return hbmp


def update_window(hwnd, img, x, y):
    hbmp = pil_to_hbitmap(img)
    hdc_screen = user32.GetDC(None)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    old = gdi32.SelectObject(hdc_mem, hbmp)
    pt_dst, sz, pt_src = wt.POINT(x, y), wt.SIZE(img.width, img.height), wt.POINT(0, 0)
    blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
    user32.UpdateLayeredWindow(
        hwnd,
        hdc_screen,
        ctypes.byref(pt_dst),
        ctypes.byref(sz),
        hdc_mem,
        ctypes.byref(pt_src),
        0,
        ctypes.byref(blend),
        ULW_ALPHA,
    )

    # Always On Top
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

    gdi32.SelectObject(hdc_mem, old)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(None, hdc_screen)


class AppState:
    def __init__(self, builds):
        self.builds = builds
        self.current_build_idx = 0
        self.update_current_build_data()
        self.selected = 0
        self.hover = -1
        self.selecting_build = False
        self.hwnd_grid = None
        self.hwnd_list = None
        self.grid_pos = (450, 60)
        self.list_pos = (0, 0)
        self.cell_size = 28
        self.minimized = False
        self.grid_cache = {}
        self.dragging = False
        self.drag_start = (0, 0)
        self.drag_offset = (0, 0)
        self.load_config()

    def update_current_build_data(self):
        cur = self.builds[self.current_build_idx]
        self.build_name, self.boards = cur["name"], cur["boards"]
        self.grid_cache = {}

    def load_config(self):
        cfg_path = Path(CONFIG_FILE)
        if not cfg_path.exists():
            return

        try:
            with cfg_path.open("r", encoding="utf-8") as f:
                cfg = json.load(f)
        except OSError, json.JSONDecodeError, ValueError:
            return

        self.list_pos = (0, int(cfg.get("list_pos", (0, 60))[1]))
        gp = cfg.get("grid_pos")
        if gp:
            self.grid_pos = tuple(gp)
        self.cell_size = cfg.get("cell_size", 28)
        self.minimized = cfg.get("minimized", False)

        # Clamp positions to visible screen area (prevents 'overlay opened but not visible')
        with contextlib.suppress(Exception):
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
            # list window: x is always 0
            ly = max(0, min(int(self.list_pos[1]), max(0, sh - 80)))
            self.list_pos = (0, ly)
            gx, gy = self.grid_pos
            gx = max(0, min(int(gx), max(0, sw - 80)))
            gy = max(0, min(int(gy), max(0, sh - 80)))
            self.grid_pos = (gx, gy)

    def save_config(self):
        cfg = {
            "list_pos": self.list_pos,
            "grid_pos": self.grid_pos,
            "cell_size": self.cell_size,
            "minimized": self.minimized,
        }
        cfg_path = Path(CONFIG_FILE)
        try:
            with cfg_path.open("w", encoding="utf-8") as f:
                json.dump(cfg, f)
        except OSError:
            LOGGER.debug("Failed to save overlay config", exc_info=True)


state = None
CONFIG_FILE = "d4_overlay_config.json"


def redraw_all(force_grid=False):
    l_img = render_list_window(state)
    update_window(state.hwnd_list, l_img, 0, state.list_pos[1])

    if state.minimized or state.selecting_build:
        g_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    else:
        key = (state.selected, state.cell_size)
        if force_grid or key not in state.grid_cache:
            state.grid_cache[key] = render_grid_window(state.boards[state.selected], state.cell_size)
        g_img = state.grid_cache[key]
    update_window(state.hwnd_grid, g_img, state.grid_pos[0], state.grid_pos[1])


@WNDPROCTYPE
def WndProcList(hwnd, msg, wparam, lparam):
    if msg == WM_DESTROY:
        user32.PostQuitMessage(0)
        return 0
    if msg == WM_NCHITTEST:
        return HTCLIENT

    if msg == WM_MOUSEMOVE:
        if state.minimized:
            return 0
        _, y = get_xy(lparam)
        if y > HEADER_H:
            lst = state.builds if state.selecting_build else state.boards
            idx = (y - HEADER_H - 10) // (ITEM_H + 4)
            nh = idx if 0 <= idx < len(lst) else -1
            if nh != state.hover:
                state.hover = nh
                redraw_all()
        elif state.hover != -1:
            state.hover = -1
            redraw_all()
        return 0

    if msg == WM_LBUTTONDOWN:
        user32.SetFocus(hwnd)
        x, y = get_xy(lparam)
        # Check START/STOP Button
        if x < 28 and y < 28:
            state.minimized = not state.minimized
            state.save_config()
            redraw_all()
            return 0

        if state.minimized:
            return 0

        # Check EXIT Button
        # Rect: [PANEL_W - 35, 55, PANEL_W - 10, 80]
        if PANEL_W - 35 <= x <= PANEL_W - 10 and 55 <= y <= 80:
            user32.PostQuitMessage(0)
            return 0

        if y < HEADER_H:
            if x > 30:
                state.selecting_build = not state.selecting_build
                state.hover = -1
                redraw_all()
            return 0

        lst = state.builds if state.selecting_build else state.boards
        idx = (y - HEADER_H - 10) // (ITEM_H + 4)
        if 0 <= idx < len(lst):
            if state.selecting_build:
                state.current_build_idx = idx
                state.update_current_build_data()
                state.selected = 0
                state.selecting_build = False
            else:
                state.selected = idx
            redraw_all()
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


@WNDPROCTYPE
def WndProcGrid(hwnd, msg, wparam, lparam):
    if msg == WM_NCHITTEST:
        return HTCLIENT

    if msg == WM_MOUSEWHEEL:
        delta = ctypes.c_short(wparam >> 16).value
        change = 2 if delta > 0 else -2
        new_size = max(10, min(150, state.cell_size + change))
        if new_size != state.cell_size:
            state.cell_size = new_size
            state.save_config()
            redraw_all(True)
        return 0

    if msg == WM_LBUTTONDOWN:
        user32.SetFocus(hwnd)
        user32.SetCapture(hwnd)
        state.dragging = True
        pt = wt.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        state.drag_start = (pt.x, pt.y)
        state.drag_offset = state.grid_pos
        user32.SetCursor(user32.LoadCursorW(state.h_inst, wt.LPCWSTR(IDC_SIZEALL)))
        return 0

    if msg == WM_MOUSEMOVE:
        if state.dragging:
            pt = wt.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            dx = pt.x - state.drag_start[0]
            dy = pt.y - state.drag_start[1]
            state.grid_pos = (state.drag_offset[0] + dx, state.drag_offset[1] + dy)
            redraw_all(False)
        return 0

    if msg == WM_LBUTTONUP:
        if state.dragging:
            state.dragging = False
            user32.ReleaseCapture()
            state.save_config()
            user32.SetCursor(user32.LoadCursorW(state.h_inst, wt.LPCWSTR(IDC_ARROW)))
        return 0

    if msg == WM_KEYDOWN:
        gx, gy = state.grid_pos
        step = 10 if (user32.GetKeyState(VK_SHIFT) & 0x8000) else 1
        if wparam == VK_LEFT:
            state.grid_pos = (gx - step, gy)
        elif wparam == VK_RIGHT:
            state.grid_pos = (gx + step, gy)
        elif wparam == VK_UP:
            state.grid_pos = (gx, gy - step)
        elif wparam == VK_DOWN:
            state.grid_pos = (gx, gy + step)
        if wparam in (VK_LEFT, VK_RIGHT, VK_UP, VK_DOWN):
            state.save_config()
            redraw_all()

    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


def run_paragon_overlay(preset_path: str | None = None) -> None:
    global state
    preset = preset_path or (sys.argv[1] if len(sys.argv) > 1 else "AffixPresets-v2.json")
    try:
        builds = load_builds_from_path(preset)
    except Exception as e:
        # In packaged mode we often suppress stdout/stderr; show a visible error.
        LOGGER.exception("Failed to load Paragon preset(s): %s", preset)
        _msgbox("D4LF Paragon Overlay", f"Konnte Paragon JSON nicht laden.\n\nQuelle: {preset}\n\nFehler: {e}")
        return

    state = AppState(builds)
    state.h_inst = kernel32.GetModuleHandleW(None)

    wc = WNDCLASSW(
        style=0,
        lpfnWndProc=WndProcList,
        hInstance=state.h_inst,
        hCursor=user32.LoadCursorW(state.h_inst, wt.LPCWSTR(IDC_ARROW)),
        lpszClassName="D4ListCls",
    )
    user32.RegisterClassW(ctypes.byref(wc))

    wc.lpfnWndProc = WndProcGrid
    wc.lpszClassName = "D4GridCls"
    user32.RegisterClassW(ctypes.byref(wc))

    ex_style = WS_EX_TOPMOST | WS_EX_LAYERED | WS_EX_TOOLWINDOW

    # Init default to Top-Left if config not loaded
    if state.list_pos == (0, 0) and state.grid_pos == (450, 60):
        state.list_pos = (0, 0)
        state.grid_pos = (600, 50)

    state.hwnd_list = user32.CreateWindowExW(
        ex_style,
        "D4ListCls",
        "List",
        WS_POPUP | WS_VISIBLE,
        0,
        state.list_pos[1],
        400,
        600,
        None,
        None,
        state.h_inst,
        None,
    )
    state.hwnd_grid = user32.CreateWindowExW(
        ex_style,
        "D4GridCls",
        "Grid",
        WS_POPUP | WS_VISIBLE,
        state.grid_pos[0],
        state.grid_pos[1],
        800,
        800,
        None,
        None,
        state.h_inst,
        None,
    )

    redraw_all(True)
    msg = wt.MSG()
    while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0):
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


if __name__ == "__main__":
    run_paragon_overlay()
