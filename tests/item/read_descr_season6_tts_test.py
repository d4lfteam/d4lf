import pytest

import src.tts
from src.item.data.affix import AffixType
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr_tts import read_descr
from src.item.models import Affix, Item

items = [
    (
        [
            "BLOOD BOILING LOOP OF BALEFUL INTENT",
            "Legendary Ring",
            "750 Item Power",
            "+10.0% Resistance to All Elements",
            "+10.0% Cold Resistance",
            "+97 Dexterity",
            "+261 Maximum Life",
            "+54.0% Overpower Damage",
            "When your Core Skills Overpower an enemy, you spawn 3 Volatile Blood Drops. Collecting a Volatile Blood Drop causes it to explode, dealing 813 Physical damage around you.. Every 20 seconds, your next Skill is guaranteed to Overpower.",
            "Empty Socket",
            "Requires Level 60",
            "Sell Value: 45,145 Gold",
            "Tempers: 5/5",
            "Mousewheel scroll down",
            "Scroll Down",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(name="dexterity", type=AffixType.greater, value=97),
                Affix(name="maximum_life", type=AffixType.greater, value=261),
                Affix(name="overpower_damage", type=AffixType.greater, value=54),
            ],
            inherent=[
                Affix(name="resistance_to_all_elements", type=AffixType.inherent, value=10),
                Affix(name="cold_resistance", type=AffixType.inherent, value=10),
            ],
            item_type=ItemType.Ring,
            power=750,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        [
            "TORMENTORS GOLDEN QUARTERSTAFF",
            "Legendary Quarterstaff",
            "750 Item Power",
            "523 Damage Per Second  (-73)",
            "[381 - 571] Damage per Hit",
            "1.10 Attacks per Second (Fast)",
            "40% Block Chance",
            "+182 Dexterity",
            "+544 Maximum Life",
            "+112.0% Damage Over Time",
            "Enemies who move while Poisoned by you additionally take 160% of your Thorns damage per second.",
            "Empty Socket",
            "Empty Socket",
            "Requires Level 60. Spiritborn. Vessel of Hatred Item",
            "Sell Value: 82,765 Gold",
            "Durability: 100/100. Tempers: 5/5",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(name="dexterity", type=AffixType.greater, value=182),
                Affix(name="maximum_life", type=AffixType.greater, value=544),
                Affix(name="damage_over_time", type=AffixType.greater, value=112),
            ],
            inherent=[Affix(name="block_chance", type=AffixType.inherent, value=40)],
            item_type=ItemType.Quarterstaff,
            power=750,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        [
            "TORMENTORS ELEGANT POLEARM",
            "Legendary Polearm",
            "750 Item Power",
            "523 Damage Per Second",
            "[466 - 698] Damage per Hit",
            "0.90 Attacks per Second (Slow)",
            "+76.5% Vulnerable Damage [76.5]%",
            "+185 Dexterity +[178 - 198]",
            "+2 Vigor On Kill +[2]",
            "+72.0% Vulnerable Damage [70.0 - 90.0]%",
            "Enemies who move while Poisoned by you additionally take 280% [100 - 380]% of your Thorns damage per second.",
            "Empty Socket",
            "Empty Socket",
            "Requires Level 60. Spiritborn. Vessel of Hatred Item",
            "Sell Value: 82,765 Gold",
            "Durability: 100/100. Tempers: 5/5",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(max_value=198.0, min_value=178.0, name="dexterity", type=AffixType.normal, value=185.0),
                Affix(max_value=2.0, min_value=2.0, name="vigor_on_kill", type=AffixType.normal, value=2.0),
                Affix(max_value=90.0, min_value=70.0, name="vulnerable_damage", type=AffixType.normal, value=72.0),
            ],
            inherent=[Affix(max_value=76.5, min_value=76.5, name="vulnerable_damage", type=AffixType.inherent, value=76.5)],
            item_type=ItemType.Polearm,
            power=750,
            rarity=ItemRarity.Legendary,
        ),
    ),
]


@pytest.mark.parametrize(("input_item", "expected_item"), items)
def test_items(input_item: list[str], expected_item: Item):
    src.tts.LAST_ITEM = input_item
    item = read_descr()
    assert item == expected_item
