import logging
import threading
import time

import mss
import mss.windows
import numpy as np

from src.config.ui import ResManager
from src.utils.misc import convert_args_to_numpy

LOGGER = logging.getLogger(__name__)

mss.windows.CAPTUREBLT = 0
cached_img_lock = threading.Lock()


class Cam:
    last_grab: int = None
    cached_img: np.ndarray = None
    window_offset_set: bool = False
    window_roi: dict = {"top": 0, "left": 0, "width": 0, "height": 0}
    monitor_x_range: tuple[int] = None
    monitor_y_range: tuple[int] = None
    res_key = ""

    _initialized: bool = False
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def update_window_pos(self, offset_x: int, offset_y: int, width: int, height: int):
        if (
            self.is_offset_set()
            and self.window_roi["top"] == offset_y
            and self.window_roi["left"] == offset_x
            and self.window_roi["width"] == width
            and self.window_roi["height"] == height
        ):
            return
        self.res_key = f"{width}x{height}"
        self.res_p = f"{height}p"
        LOGGER.debug(f"Found Window Res: {self.res_key}")

        self.window_roi["top"] = offset_y
        self.window_roi["left"] = offset_x
        self.window_roi["width"] = width
        self.window_roi["height"] = height
        self.monitor_x_range = (self.window_roi["left"] + 10, self.window_roi["left"] + self.window_roi["width"] - 10)
        self.monitor_y_range = (self.window_roi["top"] + 10, self.window_roi["top"] + self.window_roi["height"] - 10)
        self.window_offset_set = True
        ResManager().set_resolution(self.res_key)
        if self.window_roi["width"] / self.window_roi["height"] < 16 / 10:
            LOGGER.warning("Aspect ratio is too narrow, please use a wider window. At least 16/10")

    def is_offset_set(self):
        return self.window_offset_set

    def grab(self, force_new: bool = False) -> np.ndarray:
        if (
            not force_new
            and self.cached_img is not None
            and self.last_grab is not None
            and time.perf_counter() - self.last_grab < 0.04
        ):
            return self.cached_img

        # wait for offsets to be found
        if not self.is_offset_set():
            LOGGER.debug("Wait for window detection")
            while not self.window_offset_set:
                time.sleep(0.05)
            LOGGER.debug("Found window, continue grabbing")
        with cached_img_lock:
            self.last_grab = time.perf_counter()
        with mss.mss() as sct:
            img = np.array(sct.grab(self.window_roi))
        with cached_img_lock:
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
