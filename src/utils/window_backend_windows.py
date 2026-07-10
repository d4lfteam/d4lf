import ctypes
import logging
import os
import threading
import time

import psutil
from win32gui import ClientToScreen, EnumWindows, GetClientRect, GetWindowText
from win32process import GetWindowThreadProcessId

from src.cam import Cam

LOGGER = logging.getLogger(__name__)

DETECTION_WINDOW_FLAG = True
DETECT_WINDOW_THREAD = None


def list_active_window_ids() -> list[int]:
    window_list = []
    EnumWindows(lambda win, list_of_win: list_of_win.append(win), window_list)
    return window_list


def get_window_name_from_id(hwnd: int) -> str:
    return GetWindowText(hwnd)


def get_process_from_window_name(hwnd: int) -> str:
    try:
        pid = GetWindowThreadProcessId(hwnd)[1]
        return psutil.Process(pid).name().lower()
    except psutil.Error, OSError:
        return ""


def get_window_spec_id(window_spec) -> int | None:
    for hwnd in list_active_window_ids():
        if window_spec.match(hwnd):
            return hwnd
    # If no process was found with "diablo" in the window name, search without that restriction
    for hwnd in list_active_window_ids():
        if window_spec.match(hwnd, check_window_name=False):
            return hwnd
    return None


def start_detecting_window(window_spec):
    global DETECTION_WINDOW_FLAG, DETECT_WINDOW_THREAD
    if DETECT_WINDOW_THREAD is None:
        LOGGER.info(f"Using WinAPI to search for window: {window_spec.process_name}")
        DETECTION_WINDOW_FLAG = True
        DETECT_WINDOW_THREAD = threading.Thread(target=detect_window, args=(window_spec,), daemon=True)
        DETECT_WINDOW_THREAD.start()


def detect_window(window_spec):
    global DETECTION_WINDOW_FLAG
    while DETECTION_WINDOW_FLAG:
        find_and_set_window_position(window_spec)
    LOGGER.debug("Detect window thread stopped")


def find_and_set_window_position(window_spec):
    hwnd = get_window_spec_id(window_spec)
    if hwnd is not None:
        pos = GetClientRect(hwnd)
        top_left = ClientToScreen(hwnd, (pos[0], pos[1]))
        if pos[2] > 0 and pos[3] > 0:
            Cam().update_window_pos(top_left[0], top_left[1], pos[2], pos[3])
    time.sleep(1)


def stop_detecting_window():
    global DETECTION_WINDOW_FLAG, DETECT_WINDOW_THREAD
    DETECTION_WINDOW_FLAG = False
    if DETECT_WINDOW_THREAD:
        DETECT_WINDOW_THREAD.join()
    DETECT_WINDOW_THREAD = None


def move_window_to_foreground(window_spec):
    hwnd = get_window_spec_id(window_spec)
    if hwnd is not None:
        ctypes.windll.user32.ShowWindow(hwnd, 5)
        ctypes.windll.user32.SetForegroundWindow(hwnd)


def is_window_foreground(window_spec) -> bool:
    hwnd = get_window_spec_id(window_spec)
    if hwnd is not None:
        active_window_handle = ctypes.windll.user32.GetForegroundWindow()
        return active_window_handle == hwnd
    return False


def is_self_foreground() -> bool:
    """Check if the current process's window is in the foreground."""
    try:
        fg_win = ctypes.windll.user32.GetForegroundWindow()
        if not fg_win:
            return False
        lpdw_pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(fg_win, ctypes.byref(lpdw_pid))
        return lpdw_pid.value == os.getpid()
    except AttributeError, OSError:
        return False
