import src.tts
from src.item.descr.read_descr_tts import read_descr

LOOT_FILTER_TTS = ["SELECT ALL", "Checkbox Disabled", "Item Power Range", "Left mouse button"]


def test_loot_filter_controls_are_not_tts_item_start():
    assert src.tts.find_item_start(LOOT_FILTER_TTS) is None


def test_loot_filter_controls_do_not_raise_tts_parser_error():
    src.tts.LAST_ITEM = LOOT_FILTER_TTS

    assert read_descr() is None
