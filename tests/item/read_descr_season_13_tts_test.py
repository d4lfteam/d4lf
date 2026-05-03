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
        # In season 13 weapons have nothing we'd consider an inherent
        [
            "VICTORY SPINE",
            "Rare Sword",
            "850 Item Power",
            "1,406 Damage Per Second (-26)",
            "[1,023 - 1,535] Damage per Hit",
            "1.10 Attacks per Second (Fast)",
            "+1,802 Maximum Life [1,526 - 1,830]",
            "x7% All Damage Multiplier [6 - 10]%",
            "x24% Critical Strike Damage Multiplier [13 - 25]%",
            "Lucky Hit: Up to a 15% Chance to Restore +4 Primary Resource [3 - 4]",
            "Requires Level 70. Account Bound",
            "Sell Value: 13,381 Gold",
            "Durability: 100/100. Tempers: 1/1",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(
                    max_value=1830.0,
                    min_value=1526.0,
                    name="maximum_life",
                    text="+1,802 Maximum Life [1,526 - 1,830]",
                    type=AffixType.normal,
                    value=1802.0,
                ),
                Affix(
                    max_value=10.0,
                    min_value=6.0,
                    name="all_damage_multiplier",
                    text="x7% All Damage Multiplier [6 - 10]%",
                    type=AffixType.normal,
                    value=7.0,
                ),
                Affix(
                    max_value=25.0,
                    min_value=13.0,
                    name="critical_strike_damage_multiplier",
                    text="x24% Critical Strike Damage Multiplier [13 - 25]%",
                    type=AffixType.normal,
                    value=24.0,
                ),
                Affix(
                    max_value=4.0,
                    min_value=3.0,
                    name="lucky_hit_up_to_a_chance_to_restore_primary_resource",
                    text="Lucky Hit: Up to a 15% Chance to Restore +4 Primary Resource [3 - 4]",
                    type=AffixType.normal,
                    value=4.0,
                ),
            ],
            aspect=None,
            codex_upgrade=False,
            cosmetic_upgrade=False,
            inherent=[],
            is_in_shop=False,
            item_type=ItemType.Sword,
            name="victory_spine",
            original_name="VICTORY SPINE",
            power=850,
            rarity=ItemRarity.Rare,
            seasonal_attribute=None,
        ),
    ),
    # Boots also lost their inherents
    (
        [
            "MARCH INCEPTION",
            "Rare Boots",
            "850 Item Power",
            "638 Armor (-8.8% Toughness)",
            "+933 Armor [780 - 980]",
            "+22% Movement Speed [20 - 24]%",
            "+439 Shadow Resistance [416 - 523]",
            "Evade Grants +114% Movement Speed for 1.5 Seconds [100 - 125]%[1.5]",
            "Requires Level 70",
            "Sell Value: 10,705 Gold",
            "Durability: 100/100. Tempers: 1/1",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(
                    max_value=980.0,
                    min_value=780.0,
                    name="armor",
                    text="+933 Armor [780 - 980]",
                    type=AffixType.normal,
                    value=933.0,
                ),
                Affix(
                    max_value=24.0,
                    min_value=20.0,
                    name="movement_speed",
                    text="+22% Movement Speed [20 - 24]%",
                    type=AffixType.normal,
                    value=22.0,
                ),
                Affix(
                    max_value=523.0,
                    min_value=416.0,
                    name="shadow_resistance",
                    text="+439 Shadow Resistance [416 - 523]",
                    type=AffixType.normal,
                    value=439.0,
                ),
                Affix(
                    max_value=None,
                    min_value=None,
                    name="evade_grants_movement_speed_for_seconds",
                    text="Evade Grants +114% Movement Speed for 1.5 Seconds [100 - 125]%[1.5]",
                    type=AffixType.greater,
                    value=1.5,
                ),
            ],
            aspect=None,
            codex_upgrade=False,
            cosmetic_upgrade=False,
            inherent=[],
            is_in_shop=False,
            item_type=ItemType.Boots,
            name="march_inception",
            original_name="MARCH INCEPTION",
            power=850,
            rarity=ItemRarity.Rare,
            seasonal_attribute=None,
        ),
    ),
    # This is just to ensure 3 affix rares still work
    (
        [
            "RIP NEXUS",
            "Rare Sword",
            "850 Item Power",
            "1,406 Damage Per Second (-26)",
            "[1,023 - 1,535] Damage per Hit",
            "1.10 Attacks per Second (Fast)",
            "+126 Dexterity +[125 - 149]",
            "+1,759 Maximum Life [1,526 - 1,830]",
            "x8% All Damage Multiplier [6 - 10]%",
            "Requires Level 70. Account Bound. Lord of Hatred Item",
            "Sell Value: 13,381 Gold",
            "Durability: 100/100. Tempers: 1/1",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(
                    max_value=149.0,
                    min_value=125.0,
                    name="dexterity",
                    text="+126 Dexterity +[125 - 149]",
                    type=AffixType.normal,
                    value=126.0,
                ),
                Affix(
                    max_value=1830.0,
                    min_value=1526.0,
                    name="maximum_life",
                    text="+1,759 Maximum Life [1,526 - 1,830]",
                    type=AffixType.normal,
                    value=1759.0,
                ),
                Affix(
                    max_value=10.0,
                    min_value=6.0,
                    name="all_damage_multiplier",
                    text="x8% All Damage Multiplier [6 - 10]%",
                    type=AffixType.normal,
                    value=8.0,
                ),
            ],
            aspect=None,
            codex_upgrade=False,
            cosmetic_upgrade=False,
            inherent=[],
            is_in_shop=False,
            item_type=ItemType.Sword,
            name="rip_nexus",
            original_name="RIP NEXUS",
            power=850,
            rarity=ItemRarity.Rare,
            seasonal_attribute=None,
        ),
    ),
    # Shields also lost an inherent
    (
        [
            "CONCEITED DREAD SHIELD",
            "Legendary Shield",
            "767 Item Power",
            "863 Armor (-12.5% Toughness)",
            "20.0% Block Chance [20.0]%",
            "+100% Main Hand Weapon Damage [100]%",
            "+93 Strength +[85 - 102] (-11)",
            "+514 Thorns [386 - 579] (+514)",
            "+7.0% Healing Received [7.0 - 11.0]% (+7.0%)",
            "8.8% Damage Reduction [7.0 - 11.0]% (-1.8%)",
            "Deal 50%[x] [40 - 55]% increased damage while you have a Barrier active.",
            "Empty Socket",
            "Properties lost when equipped:",
            "+6.0% Critical Strike Chance",
            "Rampage: +6.0% Cooldown Reduction per Kill Streak Tier",
            "+100 All Stats",
            "+668 Maximum Life",
            "Legendary Power",
            "Requires Level 60",
            "Sell Value: 26,829 Gold",
            "Durability: 100/100. Tempers: 3/3",
            "Mousewheel scroll down",
            "Scroll Down",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(
                    max_value=102.0,
                    min_value=85.0,
                    name="strength",
                    text="+93 Strength +[85 - 102] (-11)",
                    type=AffixType.normal,
                    value=93.0,
                ),
                Affix(
                    max_value=579.0,
                    min_value=386.0,
                    name="thorns",
                    text="+514 Thorns [386 - 579] (+514)",
                    type=AffixType.normal,
                    value=514.0,
                ),
                Affix(
                    max_value=11.0,
                    min_value=7.0,
                    name="healing_received",
                    text="+7.0% Healing Received [7.0 - 11.0]% (+7.0%)",
                    type=AffixType.normal,
                    value=7.0,
                ),
                Affix(
                    max_value=11.0,
                    min_value=7.0,
                    name="damage_reduction",
                    text="8.8% Damage Reduction [7.0 - 11.0]% (-1.8%)",
                    type=AffixType.normal,
                    value=8.8,
                ),
            ],
            aspect=Aspect(
                name="conceited", text="Deal 50%[x] [40 - 55]% increased damage while you have a Barrier active."
            ),
            codex_upgrade=False,
            cosmetic_upgrade=False,
            inherent=[],
            is_in_shop=False,
            item_type=ItemType.Shield,
            name="conceited_dread_shield",
            original_name="CONCEITED DREAD SHIELD",
            power=767,
            rarity=ItemRarity.Legendary,
            seasonal_attribute=None,
        ),
    ),
]


@pytest.mark.parametrize(("input_item", "expected_item"), items)
def test_items(input_item: list[str], expected_item: Item):
    src.tts.LAST_ITEM = input_item
    item = read_descr()
    assert item == expected_item
