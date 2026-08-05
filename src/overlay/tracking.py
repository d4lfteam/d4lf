import threading
import time
from typing import TYPE_CHECKING

from src.automation import move_pointer
from src.overlay import state as _state
from src.overlay.settings import InfoSettingValue, load_settings, setting_position
from src.overlay.singleton import singleton
from src.overlay.statistics import SessionStats
from src.perception import abs_window_to_monitor, game_window_roi, window_to_monitor
from src.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import Callable


def _not_busy() -> bool:
    return False


_busy_checker: Callable[[], bool] = _not_busy


def set_busy_checker(checker: Callable[[], bool]) -> None:
    global _busy_checker
    _busy_checker = checker


def _hover_experience_balance(config: dict[str, InfoSettingValue]) -> None:
    position = setting_position(config.get("exp_bar_pos"))
    if position and len(position) == 4:
        move_pointer(*window_to_monitor((position[0], position[1])))
        time.sleep(0.1)
        move_pointer(*window_to_monitor((position[2], position[3])))
        return
    roi = game_window_roi()
    if roi:
        move_pointer(*window_to_monitor((roi["width"] // 2, roi["height"] - 10)))


@singleton
class InventoryExpTracker:
    def __init__(self):
        self.last_hover_time = 0.0
        self.hover_active = False

    def on_inventory_open(self) -> None:
        if self.hover_active or _busy_checker():
            return
        if not _state.is_open():
            return
        config = load_settings()
        if not config.get("capture_exp_stats") or not config.get("check_exp_on_inventory_open", True):
            return
        age = config.get("exp_age_before_refresh", 5)
        if not isinstance(age, int):
            age = 5
        if age == -1 or get_settings().advanced_options.vision_mode_only:
            return
        now = time.time()
        interval = age * 60 if SessionStats().last_exp is not None else 2.0
        if now - self.last_hover_time < interval:
            return

        def task() -> None:
            try:
                self.hover_active = True
                time.sleep(0.5)
                _hover_experience_balance(config)
                move_pointer(*abs_window_to_monitor((0, 0)))
            finally:
                self.hover_active = False

        self.last_hover_time = now
        threading.Thread(target=task, daemon=True).start()
