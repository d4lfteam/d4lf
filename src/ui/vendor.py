import logging

from src.template_finder import SearchArgs
from src.ui.inventory_base import InventoryBase

LOGGER = logging.getLogger(__name__)


class Vendor(InventoryBase):
    def __init__(self):
        super().__init__(8, 1, is_stash=False)
        self.menu_name = "Vendor"
        self.is_open_search_args = SearchArgs(
            ref=["vendor_menu_icon", "vendor_menu_icon_1080p"],
            threshold=0.8,
            roi="vendor_menu_icon",
            use_grayscale=True,
        )
        self.curr_tab = 0
