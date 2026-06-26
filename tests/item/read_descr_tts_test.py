import src.tts
from src.item.data.item_type import ItemType
from src.item.descr.read_descr_tts import read_descr, read_descr_mixed
from src.item.models import Item

LOOT_FILTER_TTS = ["SELECT ALL", "Checkbox Disabled", "Item Power Range", "Left mouse button"]


def test_loot_filter_controls_are_not_tts_item_start():
    assert src.tts.find_item_start(LOOT_FILTER_TTS) is None


def test_loot_filter_controls_do_not_raise_tts_parser_error():
    src.tts.LAST_ITEM = LOOT_FILTER_TTS

    assert read_descr() is None


def test_mixed_parser_returns_non_equipment_items_without_image_lookup():
    src.tts.LAST_ITEM = ["GREATER MATERIALS CACHE", "Legendary Cache"]

    assert read_descr_mixed(None) == Item(item_type=ItemType.Cache, original_name="GREATER MATERIALS CACHE")


def test_mixed_parser_returns_boss_keys_without_image_lookup():
    src.tts.LAST_ITEM = ["MALIGNANT HEART", "Legendary Boss Key"]

    assert read_descr_mixed(None) == Item(item_type=ItemType.LairBossKey, original_name="MALIGNANT HEART")
