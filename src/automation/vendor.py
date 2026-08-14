import logging

from src.automation.inventory import InventoryBase
from src.perception import SearchArgs

LOGGER = logging.getLogger(__name__)


class Vendor(InventoryBase):
    def __init__(self) -> None:
        super().__init__(8, 1, is_stash=False)
        self.menu_name = "Vendor"
        self.is_open_search_args = SearchArgs(
            ref=["vendor_menu_icon", "vendor_menu_icon_1080p"],
            threshold=0.8,
            roi="vendor_menu_icon",
            use_grayscale=True,
        )
        self.curr_tab = 0
