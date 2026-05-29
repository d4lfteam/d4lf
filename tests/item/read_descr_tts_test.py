import pytest

import src.tts
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr_tts import read_descr
from src.item.models import Item

LOOT_FILTER_TTS = ["SELECT ALL", "Checkbox Disabled", "Item Power Range", "Left mouse button"]

RARITY_TTS_LINES = [
    (ItemRarity.Common, "Common {item_type}"),
    (ItemRarity.Magic, "Magic {item_type}"),
    (ItemRarity.Rare, "Rare {item_type}"),
    (ItemRarity.Legendary, "Legendary {item_type}"),
    (ItemRarity.Unique, "Unique {item_type}"),
    (ItemRarity.Mythic, "Mythic Unique {item_type}"),
]


def test_loot_filter_controls_are_not_tts_item_start():
    assert src.tts.find_item_start(LOOT_FILTER_TTS) is None


def test_loot_filter_controls_do_not_raise_tts_parser_error():
    src.tts.LAST_ITEM = LOOT_FILTER_TTS

    assert read_descr() is None


@pytest.mark.parametrize("item_type", [ItemType.HoradricSeal, ItemType.Charm])
@pytest.mark.parametrize(("rarity", "type_line_template"), RARITY_TTS_LINES)
def test_horadric_spellcraft_items_parse_at_all_rarities(
    item_type: ItemType, rarity: ItemRarity, type_line_template: str
):
    item_name = f"TEST {item_type.value.upper()}"
    src.tts.LAST_ITEM = [item_name, type_line_template.format(item_type=item_type.value.title()), "Right mouse button"]

    assert read_descr() == Item(
        item_type=item_type, name=f"test_{item_type.value.replace(' ', '_')}", original_name=item_name, rarity=rarity
    )
