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
            "ESUS HEIRLOOM",
            "Unique Boots",
            "750 Item Power",
            "60 Armor",
            "Evade Grants +100% Movement Speed for 3.0 Seconds [100]%[3.0]",
            "+17.0% Movement Speed [16.5 - 20.0]%",
            "+10.5% Movement Speed for 7 Seconds After Killing an Elite [9.0 - 11.0]%[7]",
            "+58.0% Critical Strike Damage [52.0 - 70.0]%",
            "+10.5% Resistance to All Elements [9.0 - 10.8]%",
            "Your Critical Strike Chance is increased by 34% [20 - 40]% of your Movement Speed bonus.. Current Bonus: 17.6% [10.4 - 20.7]%",
            "While scholars have proven these boots were not created by Esu herself, it is noteworthy that they have been passed down since the formation of the Mage Clans.. - Barretts Book of Implements",
            "Requires Level 60Sorcerer. Only. Unique Equipped",
            "Sell Value: 90,289 Gold",
            "Durability: 100/100",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(
                    max_value=20.0,
                    min_value=16.5,
                    name="movement_speed",
                    text="+17.0% Movement Speed [16.5 - 20.0]%",
                    type=AffixType.normal,
                    value=17.0,
                ),
                Affix(
                    max_value=11.0,
                    min_value=9.0,
                    name="movement_speed_for_seconds_after_killing_an_elite",
                    text="+10.5% Movement Speed for 7 Seconds After Killing an Elite [9.0 - 11.0]%[7]",
                    type=AffixType.normal,
                    value=10.5,
                ),
                Affix(
                    max_value=70.0,
                    min_value=52.0,
                    name="critical_strike_damage",
                    text="+58.0% Critical Strike Damage [52.0 - 70.0]%",
                    type=AffixType.normal,
                    value=58.0,
                ),
                Affix(
                    max_value=10.8,
                    min_value=9.0,
                    name="resistance_to_all_elements",
                    text="+10.5% Resistance to All Elements [9.0 - 10.8]%",
                    type=AffixType.normal,
                    value=10.5,
                ),
            ],
            aspect=Aspect(
                name="esus_heirloom",
                min_value=20.0,
                max_value=40.0,
                text="Your Critical Strike Chance is increased by 34% [20 - 40]% of your Movement Speed bonus.. Current Bonus: 17.6% [10.4 - 20.7]%",
                value=34.0,
            ),
            codex_upgrade=False,
            cosmetic_upgrade=False,
            inherent=[
                Affix(
                    max_value=None,
                    min_value=None,
                    name="evade_grants_movement_speed_for_seconds",
                    text="Evade Grants +100% Movement Speed for 3.0 Seconds [100]%[3.0]",
                    type=AffixType.inherent,
                    value=3.0,
                )
            ],
            item_type=ItemType.Boots,
            name="esus_heirloom",
            power=750,
            rarity=ItemRarity.Unique,
        ),
    ),
    (
        [
            "FISTS OF FATE",
            "Unique Gloves",
            "750 Item Power",
            "60 Armor  (-4)",
            "+2.6% Attack Speed [0.1 - 8.7]% (+2.6%)",
            "+8.1% Critical Strike Chance [0.1 - 8.7]% (+8.1%)",
            "+51.0% Lucky Hit Chance [1.0 - 51.8]% (+51.0%)",
            "Lucky Hit: Up to a +30.0% Chance to Make Enemies Vulnerable for 3 Seconds [1.0 - 51.8]%[3] (+30.0%)",
            "Your attacks randomly deal 1% to 205% [200 - 300]% of their normal damage.",
            "Properties lost when equipped:",
            "+4 to Primordial Binding",
            "+2 to Familiar",
            "+53.5% Familiar Explosion Size",
            "+27.5% Chance for Familiars to Hit Twice",
            "Unique Power",
            "Will you let fear cheat you, or will you risk everything to find understanding? After all, death is simply the coin with which we purchase life.. - Zurke",
            "Requires Level 60. Account Bound. Unique Equipped",
            "Sell Value: 90,289 Gold",
            "Durability: 100/100",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(
                    max_value=8.7,
                    min_value=0.1,
                    name="attack_speed",
                    text="+2.6% Attack Speed [0.1 - 8.7]% (+2.6%)",
                    type=AffixType.normal,
                    value=2.6,
                ),
                Affix(
                    max_value=8.7,
                    min_value=0.1,
                    name="critical_strike_chance",
                    text="+8.1% Critical Strike Chance [0.1 - 8.7]% (+8.1%)",
                    type=AffixType.normal,
                    value=8.1,
                ),
                Affix(
                    max_value=51.8,
                    min_value=1.0,
                    name="lucky_hit_chance",
                    text="+51.0% Lucky Hit Chance [1.0 - 51.8]% (+51.0%)",
                    type=AffixType.normal,
                    value=51.0,
                ),
                Affix(
                    max_value=51.8,
                    min_value=1.0,
                    name="lucky_hit_up_to_a_chance_to_make_enemies_vulnerable_for_seconds",
                    text="Lucky Hit: Up to a +30.0% Chance to Make Enemies Vulnerable for 3 Seconds [1.0 - 51.8]%[3] (+30.0%)",
                    type=AffixType.normal,
                    value=30.0,
                ),
            ],
            aspect=Aspect(
                name="fists_of_fate",
                min_value=200.0,
                max_value=300.0,
                text="Your attacks randomly deal 1% to 205% [200 - 300]% of their normal damage.",
                value=205.0,
            ),
            codex_upgrade=False,
            cosmetic_upgrade=False,
            inherent=[],
            item_type=ItemType.Gloves,
            name="fists_of_fate",
            power=750,
            rarity=ItemRarity.Unique,
        ),
    ),
]


@pytest.mark.parametrize(("input_item", "expected_item"), items)
def test_items(input_item: list[str], expected_item: Item):
    src.tts.LAST_ITEM = input_item
    item = read_descr()
    assert item == expected_item
