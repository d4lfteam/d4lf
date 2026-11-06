import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.automation import move_pointer
from src.overlay.settings import InfoSettingValue, load_settings, setting_bool, setting_position
from src.overlay.statistics import SessionStats
from src.overlay.widget.shared import BOSS_TIMER_SLOT
from src.perception import abs_window_to_monitor, game_window_roi, window_to_monitor
from src.settings import get_settings
from src.singleton import singleton

if TYPE_CHECKING:
    from collections.abc import Callable

EXP_BAR_POS_VALUE_COUNT = 4


def _not_busy() -> bool:
    return False


@dataclass
class _TrackingState:
    busy_checker: Callable[[], bool] = _not_busy


_STATE = _TrackingState()


def set_busy_checker(checker: Callable[[], bool]) -> None:
    _STATE.busy_checker = checker


def _hover_experience_balance(config: dict[str, InfoSettingValue]) -> None:
    position = setting_position(config.get("exp_bar_pos"))
    if position is not None and len(position) == EXP_BAR_POS_VALUE_COUNT:
        move_pointer(*window_to_monitor((position[0], position[1])))
        time.sleep(0.1)
        move_pointer(*window_to_monitor((position[2], position[3])))
        return
    roi = game_window_roi()
    if roi:
        move_pointer(*window_to_monitor((roi["width"] // 2, roi["height"] - 10)))


@singleton
class InventoryExpTracker:
    def __init__(self) -> None:
        self.last_hover_time = 0.0
        self.hover_active = False

    def on_inventory_open(self) -> None:
        if self.hover_active or _STATE.busy_checker():
            return
        if not BOSS_TIMER_SLOT.is_open():
            return
        config = load_settings()
        capture_exp = setting_bool(config, "capture_exp_stats")
        check_on_open = setting_bool(config, "check_exp_on_inventory_open")
        if not capture_exp or not check_on_open:
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
