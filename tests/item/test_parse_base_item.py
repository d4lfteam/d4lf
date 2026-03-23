from types import SimpleNamespace

from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.data.seasonal_attribute import SeasonalAttribute
from src.item.descr.parse_base_item import create_base_item_from_tts


def _loader(*, bad_tts_uniques=None):
    return SimpleNamespace(bad_tts_uniques=bad_tts_uniques or {})


def test_compass_maps_to_common_compass():
    item = create_base_item_from_tts(["Some Compass", "Ancient Compass"], dataloader=_loader())
    assert item.item_type == ItemType.Compass
    assert item.rarity == ItemRarity.Common


def test_nightmare_sigil_sets_bloodied_when_present():
    item = create_base_item_from_tts(
        ["Nightmare Sigil of Doom", "bloodied nightmare sigil"], dataloader=_loader()
    )
    assert item.item_type == ItemType.Sigil
    assert item.rarity == ItemRarity.Common
    assert item.seasonal_attribute == SeasonalAttribute.bloodied


def test_nightmare_sigil_used_screen_returns_none():
    assert create_base_item_from_tts(["Nightmare Sigil is used", "anything"], dataloader=_loader()) is None


def test_tribute_names_are_normalized():
    item = create_base_item_from_tts(["TRIBUTE OF PRIDE", "Magic Tribute of Pride"], dataloader=_loader())
    assert item.item_type == ItemType.Tribute
    assert item.rarity == ItemRarity.Magic
    assert item.name == "tribute_of_pride"


def test_consumable_and_special_items_are_classified():
    cases = [
        (["WHISPERING KEY", "WHISPERING KEY"], ItemType.Consumable),
        (["Any", "Mysterious summoning"], ItemType.Material),
        (["Any", "Shiny gem"], ItemType.Gem),
        (["Any", "Ancient whispering wood"], ItemType.WhisperingWood),
        (["Any", "Cosmetic appearance"], ItemType.Cosmetic),
        (["Any", "Dungeon boss key"], ItemType.LairBossKey),
        (["Any", "Legendary cache"], ItemType.Cache),
    ]

    for tts_item, expected_type in cases:
        item = create_base_item_from_tts(tts_item, dataloader=_loader())
        assert item.item_type == expected_type


def test_rune_and_consumable_text_still_set_rarity():
    rune = create_base_item_from_tts(["Any", "Rare rune of storm"], dataloader=_loader())
    assert rune.item_type == ItemType.Rune
    assert rune.rarity == ItemRarity.Rare

    consumable = create_base_item_from_tts(["Any", "Magic scroll"], dataloader=_loader())
    assert consumable.item_type == ItemType.Consumable
    assert consumable.rarity == ItemRarity.Magic


def test_sanctified_and_shop_detection_and_bad_unique_remap():
    item = create_base_item_from_tts(
        ["Bad Unique", "Legendary sword", "Line 3", "Line 4 sanctified", "Item Power: 925"],
        dataloader=_loader(bad_tts_uniques={"bad_unique": "good_unique"}),
    )
    assert item.seasonal_attribute == SeasonalAttribute.sanctified
    assert item.is_in_shop is False
    assert item.name == "good_unique"


def test_shop_flag_is_detected_from_any_line():
    item = create_base_item_from_tts(["Any", "Legendary sword", "Cost: 1"], dataloader=_loader())
    assert item.is_in_shop is True
