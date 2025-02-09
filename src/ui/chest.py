import logging
import time

from src.cam import Cam
from src.config.ui import ResManager
from src.template_finder import SearchArgs
from src.ui.inventory_base import InventoryBase
from src.utils.custom_mouse import mouse

LOGGER = logging.getLogger(__name__)


class Chest(InventoryBase):
    def __init__(self):
        super().__init__(5, 10, is_stash=True)
        self.menu_name = "Chest"
        self.is_open_search_args = SearchArgs(
            ref=["stash_menu_icon", "stash_menu_icon_medium"], threshold=0.8, roi="stash_menu_icon", use_grayscale=True
        )
        self.curr_tab = 0

    @staticmethod
    def switch_to_tab(tab_idx) -> bool:
        NUMBER_TABS = 6
        LOGGER.info(f"Switch Stash Tab to: {tab_idx}")
        if tab_idx > (NUMBER_TABS - 1):
            return False
        x, y, w, h = ResManager().roi.tab_slots_6
        section_length = w // NUMBER_TABS
        centers = [(x + (i + 0.5) * section_length, y + h // 2) for i in range(NUMBER_TABS)]
        mouse.move(*Cam().window_to_monitor(centers[tab_idx]), randomize=2)
        time.sleep(0.1)
        mouse.click("left")
        time.sleep(0.2)
        return True
