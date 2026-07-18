import logging
import threading
import time
from typing import TypedDict

import mss
import mss.windows
import numpy as np

from src.settings import get_ui_coordinates
from src.utils.misc import convert_args_to_numpy

LOGGER = logging.getLogger(__name__)

# The mss Windows module consumes this Win32 flag at runtime, but its stubs omit it.
mss.windows.__dict__["CAPTUREBLT"] = 0
cached_img_lock = threading.Lock()


class WindowROI(TypedDict):
    top: int
    left: int
    width: int
    height: int


class Cam:
    last_grab: float | None = None
    cached_img: np.ndarray | None = None
    window_offset_set: bool = False
    window_roi: WindowROI = {"top": 0, "left": 0, "width": 0, "height": 0}
    monitor_x_range: tuple[int, int] | None = None
    monitor_y_range: tuple[int, int] | None = None
    res_key = ""
    _window_generation: int = 0

    _initialized: bool = False
    _instance: Cam | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def update_window_pos(self, offset_x: int, offset_y: int, width: int, height: int):
        with cached_img_lock:
            if (
                self.window_offset_set
                and self.window_roi["top"] == offset_y
                and self.window_roi["left"] == offset_x
                and self.window_roi["width"] == width
                and self.window_roi["height"] == height
            ):
                return
            self.res_key = f"{width}x{height}"
            self.res_p = f"{height}p"
            self.window_roi["top"] = offset_y
            self.window_roi["left"] = offset_x
            self.window_roi["width"] = width
            self.window_roi["height"] = height
            self.monitor_x_range = (
                self.window_roi["left"] + 10,
                self.window_roi["left"] + self.window_roi["width"] - 10,
            )
            self.monitor_y_range = (
                self.window_roi["top"] + 10,
                self.window_roi["top"] + self.window_roi["height"] - 10,
            )
            self.window_offset_set = True
            self._window_generation += 1
            self.last_grab = None
            self.cached_img = None
            res_key = self.res_key

        LOGGER.debug(f"Found Window Res: {res_key}")

        get_ui_coordinates().set_resolution(res_key)
        if width / height < 16 / 10:
            LOGGER.warning("Aspect ratio is too narrow, please use a wider window. At least 16/10")

    def reset_window_position(self):
        with cached_img_lock:
            if not self.window_offset_set:
                return
            self.window_offset_set = False
            self.window_roi = {"top": 0, "left": 0, "width": 0, "height": 0}
            self.monitor_x_range = None
            self.monitor_y_range = None
            self.res_key = ""
            self.res_p = ""
            self._window_generation += 1
            self.last_grab = None
            self.cached_img = None
        LOGGER.info("Diablo IV window was closed; waiting for a new window.")

    def is_offset_set(self):
        return self.window_offset_set

    def grab(self, force_new: bool = False) -> np.ndarray:
        waiting_for_window = False
        while True:
            with cached_img_lock:
                if (
                    self.window_offset_set
                    and not force_new
                    and self.cached_img is not None
                    and self.last_grab is not None
                    and time.perf_counter() - self.last_grab < 0.04
                ):
                    return self.cached_img
                window_ready = self.window_offset_set
                window_roi = dict(self.window_roi)
                generation = self._window_generation

            if not window_ready:
                if not waiting_for_window:
                    LOGGER.debug("Wait for window detection")
                    waiting_for_window = True
                time.sleep(0.05)
                continue
            if waiting_for_window:
                LOGGER.debug("Found window, continue grabbing")
                waiting_for_window = False

            with mss.mss() as sct:
                img = np.array(sct.grab(window_roi))
            with cached_img_lock:
                if not self.window_offset_set or self._window_generation != generation:
                    continue
                self.last_grab = time.perf_counter()
                self.cached_img = img[:, :, :3]
                return self.cached_img

    # Conversions
    # ============================================================================
    @convert_args_to_numpy
    def monitor_to_window(self, monitor_coord: np.ndarray) -> np.ndarray:
        return monitor_coord[:] - np.array([self.window_roi["left"], self.window_roi["top"]])

    @convert_args_to_numpy
    def window_to_monitor(self, window_coord: np.ndarray) -> np.ndarray:
        # TODO: clip by monitor ranges
        return window_coord[:] + np.array([self.window_roi["left"], self.window_roi["top"]])

    @convert_args_to_numpy
    def abs_window_to_window(self, abs_window_coord: np.ndarray) -> np.ndarray:
        return abs_window_coord[:] + np.array([self.window_roi["width"] // 2, self.window_roi["height"] // 2])

    @convert_args_to_numpy
    def window_to_abs_window(self, window_coord: np.ndarray) -> np.ndarray:
        return window_coord[:] - np.array([self.window_roi["width"] // 2, self.window_roi["height"] // 2])

    @convert_args_to_numpy
    def abs_window_to_monitor(self, abs_window_coord: np.ndarray) -> np.ndarray:
        window_coord = self.abs_window_to_window(abs_window_coord)
        return self.window_to_monitor(window_coord)
