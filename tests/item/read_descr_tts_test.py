import numpy as np
import pytest

import src.tts
from src.item.data.affix import Affix
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr_tts import read_descr, read_descr_mixed
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

AFFIX_TTS_LINES = [
    "10% Cooldown Reduction [5 - 15]",
    "100 Maximum Life [50 - 150]",
    "20% Critical Strike Chance [10 - 30]",
    "12% Movement Speed [5 - 20]",
]

EXPECTED_AFFIXES = [
    Affix(text="10% Cooldown Reduction [5 - 15]", name="cooldown_reduction", value=10.0, min_value=5.0, max_value=15.0),
    Affix(text="100 Maximum Life [50 - 150]", name="maximum_life", value=100.0, min_value=50.0, max_value=150.0),
    Affix(
        text="20% Critical Strike Chance [10 - 30]",
        name="critical_strike_chance",
        value=20.0,
        min_value=10.0,
        max_value=30.0,
    ),
    Affix(text="12% Movement Speed [5 - 20]", name="movement_speed", value=12.0, min_value=5.0, max_value=20.0),
]


def test_loot_filter_controls_are_not_tts_item_start():
    assert src.tts.find_item_start(LOOT_FILTER_TTS) is None


def test_loot_filter_controls_do_not_raise_tts_parser_error():
    src.tts.LAST_ITEM = LOOT_FILTER_TTS

    assert read_descr() is None


@pytest.mark.parametrize("item_type", [ItemType.HoradricSeal, ItemType.Charm])
@pytest.mark.parametrize(("rarity", "type_line_template"), RARITY_TTS_LINES)
def test_seal_or_charm_items_parse_at_all_rarities(item_type: ItemType, rarity: ItemRarity, type_line_template: str):
    item_name = f"TEST {item_type.value.upper()}"
    expected_affix_count = _expected_affix_count(rarity)
    src.tts.LAST_ITEM = [
        item_name,
        type_line_template.format(item_type=item_type.value.title()),
        *AFFIX_TTS_LINES[:expected_affix_count],
        "Right mouse button",
    ]
    expected_item = Item(
        affixes=EXPECTED_AFFIXES[:expected_affix_count],
        item_type=item_type,
        name=f"test_{item_type.value.replace(' ', '_')}",
        original_name=item_name,
        rarity=rarity,
    )

    assert read_descr() == expected_item
    assert read_descr_mixed(np.empty((1, 1, 3), dtype=np.uint8)) == expected_item


@pytest.mark.parametrize("item_type", [ItemType.HoradricSeal, ItemType.Charm])
def test_seal_or_charm_items_parse_variable_affix_counts(item_type: ItemType):
    item_name = f"VARIABLE {item_type.value.upper()}"
    src.tts.LAST_ITEM = [
        item_name,
        f"Legendary {item_type.value.title()}",
        "10% Cooldown Reduction [5 - 15]",
        "100 Maximum Life [50 - 150]",
        "Right mouse button",
    ]
    expected_item = Item(
        affixes=EXPECTED_AFFIXES[:2],
        item_type=item_type,
        name=f"variable_{item_type.value.replace(' ', '_')}",
        original_name=item_name,
        rarity=ItemRarity.Legendary,
    )

    assert read_descr() == expected_item


def test_horadric_charm_type_line_parses_as_charm():
    src.tts.LAST_ITEM = [
        "DIVINE CHARM OF RESTORATION",
        "Legendary Horadric Charm",
        "10% Cooldown Reduction [5 - 15]",
        "Right mouse button",
    ]
    expected_item = Item(
        affixes=EXPECTED_AFFIXES[:1],
        item_type=ItemType.Charm,
        name="divine_charm_of_restoration",
        original_name="DIVINE CHARM OF RESTORATION",
        rarity=ItemRarity.Legendary,
    )

    assert read_descr() == expected_item


def test_set_charm_stops_affixes_before_set_bonus_text():
    src.tts.LAST_ITEM = [
        "LINTA OF THE FROZEN SEA",
        "Set Charm",
        "Lucky Hit: Up to a 40% Chance to Deal +650 Poison Damage",
        "+7.0% Potion Healing",
        "Breath of the Frozen Sea",
        "Phoba of the Frozen Sea",
        "Breath of the Frozen Sea (0/5). (2) Set:. Frost Skills deal 70% of their direct damage as bonus Frostbite over 12 seconds.. (3) Set:. You cannot be Chilled or Frozen.. Your Maximum Life and Barrier generation is increased by 20%.. (5) Set:. Frost Skill damage is increased by 200%.. Freezing enemies consumes all Frostbite on them, dealing its remaining damage instantly.",
        "Requires Level 70Sorcerer. Only. Unique Equipped. Lord of Hatred Item",
        "Right mouse button",
    ]
    item = read_descr()

    assert item.item_type == ItemType.Charm
    assert item.name == "linta_of_the_frozen_sea"
    assert item.set_name == "breath_of_the_frozen_sea"
    assert [affix.name for affix in item.affixes] == [
        "lucky_hit_up_to_a_chance_to_deal_poison_damage",
        "potion_healing",
    ]


def _expected_affix_count(rarity: ItemRarity) -> int:
    if rarity == ItemRarity.Common:
        return 0
    if rarity == ItemRarity.Magic:
        return 1
    if rarity == ItemRarity.Rare:
        return 3
    return 4
