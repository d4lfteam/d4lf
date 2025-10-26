import pytest

import src.tts
from src.item.data.affix import Affix, AffixType
from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr_tts import read_descr
from src.item.models import Item

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
    (
        [
            "GALVANICAZURITE",
            "Ancestral Unique Ring",
            "800 Item Power",
            "+12.5% Resistance to All Elements [12.5]%",
            "+5.0% Resistance to All Elements [5.0]%",
            "+5.8% Critical Strike Chance [5.2 - 6.0]%",
            "+73.0% Lightning Damage [57.0 - 75.0]%",
            "13.2% Cooldown Reduction",
            "+2 to Convulsions [2 - 3]",
            "Lightning damage leaves enemies magnetized for 4 seconds causing them to emit Crackling Energy, and increasing all Lightning damage they take from you by 54.0%[x] [40.0 - 60.0]%. If two magnetized enemies hit each other with Crackling Energy they pull each other together.",
            "Empty Socket",
            "This gem acts as a conduit for aetheric filaments, enabling the wielder to summon atmospheric discharge at will. - Excerpt from Volatus Arcanum: Of Skybinding and Stormcraft",
            "Requires Level 60. Account BoundSorcerer. Only. Unique Equipped",
            "Sell Value: 206,382 Gold",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(
                    max_value=6.0,
                    min_value=5.2,
                    name="critical_strike_chance",
                    text="+5.8% Critical Strike Chance [5.2 - 6.0]%",
                    type=AffixType.normal,
                    value=5.8,
                ),
                Affix(
                    max_value=75.0,
                    min_value=57.0,
                    name="lightning_damage",
                    text="+73.0% Lightning Damage [57.0 - 75.0]%",
                    type=AffixType.normal,
                    value=73.0,
                ),
                Affix(
                    max_value=None,
                    min_value=None,
                    name="cooldown_reduction",
                    text="13.2% Cooldown Reduction",
                    type=AffixType.greater,
                    value=13.2,
                ),
                Affix(
                    max_value=3.0,
                    min_value=2.0,
                    name="to_convulsions",
                    text="+2 to Convulsions [2 - 3]",
                    type=AffixType.normal,
                    value=2.0,
                ),
            ],
            aspect=Aspect(
                name="galvanic_azurite",
                min_value=40.0,
                max_value=60.0,
                text="Lightning damage leaves enemies magnetized for 4 seconds causing them to emit Crackling Energy, and increasing all Lightning damage they take from you by 54.0%[x] [40.0 - 60.0]%. If two magnetized enemies hit each other with Crackling Energy they pull each other together.",
                value=54.0,
            ),
            codex_upgrade=False,
            cosmetic_upgrade=False,
            inherent=[
                Affix(
                    max_value=12.5,
                    min_value=12.5,
                    name="resistance_to_all_elements",
                    text="+12.5% Resistance to All Elements [12.5]%",
                    type=AffixType.inherent,
                    value=12.5,
                ),
                Affix(
                    max_value=5.0,
                    min_value=5.0,
                    name="resistance_to_all_elements",
                    text="+5.0% Resistance to All Elements [5.0]%",
                    type=AffixType.inherent,
                    value=5.0,
                ),
            ],
            is_chaos=False,
            is_in_shop=False,
            item_type=ItemType.Ring,
            name="galvanic_azurite",
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
