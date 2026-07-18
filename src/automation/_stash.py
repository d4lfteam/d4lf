import logging
import time

from src.automation._inventory import InventoryBase
from src.automation._mouse import Mouse
from src.perception import TemplateQuery, create_template_query, window_to_monitor
from src.settings import get_settings, get_ui_coordinates

LOGGER = logging.getLogger(__name__)


class Stash(InventoryBase):
    def __init__(self):
        super().__init__(5, 10, is_stash=True)
        self.menu_name = "Stash"
        self.is_open_search_args: TemplateQuery = create_template_query(
            ref=["stash_menu_icon", "stash_menu_icon_medium"], threshold=0.8, roi="stash_menu_icon", use_grayscale=True
        )
        self.curr_tab = 0

    @staticmethod
    def switch_to_tab(tab_idx) -> bool:
        number_tabs = get_settings().general.max_stash_tabs
        LOGGER.info(f"Switch Stash Tab to: {tab_idx}")
        if tab_idx > (number_tabs - 1):
            return False
        x, y, w, h = get_ui_coordinates().roi.tab_slots
        section_length = w // number_tabs
        centers = [(x + (i + 0.5) * section_length, y + h // 2) for i in range(number_tabs)]
        Mouse.move(*window_to_monitor(centers[tab_idx]), randomize=2)
        Mouse.click("left")
        time.sleep(0.2)
        return True
