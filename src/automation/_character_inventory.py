from src.automation._inventory import InventoryBase
from src.perception import TemplateQuery, create_template_query
from src.settings import get_settings, get_ui_coordinates


class CharInventory(InventoryBase):
    def __init__(self):
        super().__init__()
        self.menu_name = "Char_Inventory"
        sort_icon_roi = [int(value) for value in get_ui_coordinates().roi.sort_icon]
        self.is_open_search_args: TemplateQuery = create_template_query(
            ref=["sort_icon", "sort_icon_hover"], threshold=0.8, roi=sort_icon_roi, use_grayscale=False
        )
        self.open_hotkey = get_settings().char.inventory
        self.delay = 1  # Needed as they added a "fade-in" for the items
