from src.gui.importer.maxroll import _find_item_type
from src.item.data.item_type import ItemType


def test_find_item_type_maps_maxroll_focus_alias():
    mapping_data = {"1HFocus_Legendary_Generic_005": {"type": "1HFocus"}}

    assert _find_item_type(mapping_data=mapping_data, value="1HFocus_Legendary_Generic_005") == ItemType.Focus
