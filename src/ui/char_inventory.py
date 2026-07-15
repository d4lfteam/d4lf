from src.config.loader import IniConfigLoader
from src.config.ui import ResManager
from src.template_finder import SearchArgs
from src.ui.inventory_base import InventoryBase


class CharInventory(InventoryBase):
    def __init__(self):
        super().__init__()
        self.menu_name = "Char_Inventory"
        sort_icon_roi = [int(value) for value in ResManager().roi.sort_icon]
        self.is_open_search_args: SearchArgs = SearchArgs(
            ref=["sort_icon", "sort_icon_hover"], threshold=0.8, roi=sort_icon_roi, use_grayscale=False
        )
        self.open_hotkey = IniConfigLoader().char.inventory
        self.delay = 1  # Needed as they added a "fade-in" for the items
