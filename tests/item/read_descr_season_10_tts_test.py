import pytest

import src.tts
from src.item.data.affix import AffixType
from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr_tts import read_descr
from src.item.models import Affix, Item

items = [
    (
        [
            "BAND OF FIRST BREATH",
            "Chaos Unique Chest Armor",
            "800 Item Power",
            "224 Armor",
            "+37.5% Lightning Resistance [37.5]%",
            "+130 Armor [130]",
            "10.0% Maximum Life [8.0 - 10.0]%",
            "+16.5% Critical Strike Chance",
            "+39 Vigor when Resolve is Lost",
            "+3 Maximum Resolve Stacks [2 - 4]",
            "Casting Evade consumes 1 stack of Resolve to increase your damage dealt by 48%[x] for 5 seconds.. Gain Armored Hides Passive Effect.",
            "Empty Socket",
            "A gentle whisper glides upon the winds. The words elude the grasp of mortal ken. They weave through the soul like a melody forgotten, and from this arises a name: Adarja, theFirst-Breather.",
            "Requires Level 60. Account Bound. Only. Unique Equipped. Vessel of Hatred Item",
            "Sell Value: 202,170 Gold",
            "Durability: 100/100",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(
                    max_value=10.0,
                    min_value=8.0,
                    name="maximum_life",
                    text="10.0% Maximum Life [8.0 - 10.0]%",
                    type=AffixType.normal,
                    value=10.0,
                ),
                Affix(
                    max_value=None,
                    min_value=None,
                    name="critical_strike_chance",
                    text="+16.5% Critical Strike Chance",
                    type=AffixType.greater,
                    value=16.5,
                ),
                Affix(
                    max_value=None,
                    min_value=None,
                    name="vigor_when_resolve_is_lost",
                    text="+39 Vigor when Resolve is Lost",
                    type=AffixType.greater,
                    value=39.0,
                ),
                Affix(
                    max_value=4.0,
                    min_value=2.0,
                    name="maximum_resolve_stacks",
                    text="+3 Maximum Resolve Stacks [2 - 4]",
                    type=AffixType.normal,
                    value=3.0,
                ),
            ],
            aspect=Aspect(
                name="band_of_first_breath",
                text="Casting Evade consumes 1 stack of Resolve to increase your damage dealt by 48%[x] for 5 seconds.. Gain Armored Hides Passive Effect.",
            ),
            codex_upgrade=False,
            cosmetic_upgrade=False,
            inherent=[
                Affix(
                    max_value=37.5,
                    min_value=37.5,
                    name="lightning_resistance",
                    text="+37.5% Lightning Resistance [37.5]%",
                    type=AffixType.inherent,
                    value=37.5,
                ),
                Affix(max_value=130.0, min_value=130.0, name="armor", text="+130 Armor [130]", type=AffixType.inherent, value=130.0),
            ],
            is_in_shop=False,
            is_chaos=True,
            item_type=ItemType.ChestArmor,
            name="band_of_first_breath",
            power=800,
            rarity=ItemRarity.Unique,
        ),
    ),
]


@pytest.mark.parametrize(("input_item", "expected_item"), items)
def test_items(input_item: list[str], expected_item: Item):
    src.tts.LAST_ITEM = input_item
    item = read_descr()
    assert item == expected_item
