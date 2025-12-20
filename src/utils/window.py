import ctypes
import logging
import pathlib
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import cv2
import psutil
from win32gui import ClientToScreen, EnumWindows, GetClientRect, GetWindowText
from win32process import GetWindowThreadProcessId

from src.cam import Cam
from src.logger import LOG_DIR

if TYPE_CHECKING:
    import numpy as np

LOGGER = logging.getLogger(__name__)

DETECTION_WINDOW_FLAG = True
DETECT_WINDOW_THREAD = None

# Set the process DPI aware
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    LOGGER.exception(
        "This program requires Windows 10 or higher. The program will try to continue to run, but results may be inaccurate."
    )
    ctypes.windll.user32.SetProcessDPIAware()


@dataclass
class WindowSpec:
    process_name: str

    def match(self, hwnd: int, check_window_name: bool = True) -> bool:
        window_name_ok = not check_window_name or "diablo" in _get_window_name_from_id(hwnd).lower()
        return _get_process_from_window_name(hwnd).casefold() == self.process_name.casefold() and window_name_ok


def _list_active_window_ids() -> list[int]:
    window_list = []
    EnumWindows(lambda win, list_of_win: list_of_win.append(win), window_list)
    return window_list


def get_window_spec_id(window_spec: WindowSpec) -> int | None:
    for hwnd in _list_active_window_ids():
        if window_spec.match(hwnd):
            return hwnd
    # If no process was found with "diablo" in the window name, search without that restriction
    for hwnd in _list_active_window_ids():
        if window_spec.match(hwnd, check_window_name=False):
            return hwnd
    return None


def _get_window_name_from_id(hwnd: int) -> str:
    return GetWindowText(hwnd)


def _get_process_from_window_name(hwnd: int) -> str:
    try:
        pid = GetWindowThreadProcessId(hwnd)[1]
        return psutil.Process(pid).name().lower()
    except Exception:
        return ""


def start_detecting_window(window_spec: WindowSpec):
    global DETECTION_WINDOW_FLAG, DETECT_WINDOW_THREAD
    if DETECT_WINDOW_THREAD is None:
        LOGGER.info(f"Using WinAPI to search for window: {window_spec.process_name}")
        DETECTION_WINDOW_FLAG = True
        DETECT_WINDOW_THREAD = threading.Thread(target=detect_window, args=(window_spec,), daemon=True)
        DETECT_WINDOW_THREAD.start()


def detect_window(window_spec: WindowSpec):
    global DETECTION_WINDOW_FLAG
    while DETECTION_WINDOW_FLAG:
        find_and_set_window_position(window_spec)
    LOGGER.debug("Detect window thread stopped")


def find_and_set_window_position(window_spec: WindowSpec):
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


def move_window_to_foreground(window_spec: WindowSpec):
    hwnd = get_window_spec_id(window_spec)
    if hwnd is not None:
        ctypes.windll.user32.ShowWindow(hwnd, 5)
        ctypes.windll.user32.SetForegroundWindow(hwnd)


def is_window_foreground(window_spec: WindowSpec) -> bool:
    hwnd = get_window_spec_id(window_spec)
    if hwnd is not None:
        active_window_handle = ctypes.windll.user32.GetForegroundWindow()
        return active_window_handle == hwnd
    return False


def screenshot(
    name: str | None = None,
    path: str = str(LOG_DIR / "screenshots"),
    img: np.ndarray = None,
    overwrite: bool = True,
    timestamp: bool = True,
):
    name = name if name is not None else "screenshot"
    img = img if img is not None else Cam().grab()

    pathlib.Path(path).mkdir(exist_ok=True, parents=True)
    file_path = f"{path}/{name}{'_' + datetime.now(tz=None).strftime('%Y%m%d_%H%M%S.%f') if timestamp else ''}.png"  # noqa: DTZ005

    if pathlib.Path(file_path).exists():
        if overwrite:
            LOGGER.warning(f"{name} already exists, overwriting.")
            cv2.imwrite(file_path, img)
        else:
            LOGGER.warning(f"{name} already exists, not overwriting because overwrite is set to False.")
    else:
        cv2.imwrite(file_path, img)
        LOGGER.debug(f"Saved screenshot: {file_path}")


if __name__ == "__main__":
    find_and_set_window_position(WindowSpec("Diablo IV.exe"))
