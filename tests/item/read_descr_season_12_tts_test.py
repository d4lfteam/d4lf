import pytest

import src.tts
from src.item.data.affix import Affix, AffixType
from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.data.seasonal_attribute import SeasonalAttribute
from src.item.descr.read_descr_tts import read_descr
from src.item.models import Item

items = [
    (
        # The next 3 tests are bloodied items
        [
            "INIMICAL SEAL OF PILGRIMS PROGRESS",
            "Bloodied Legendary Amulet",
            "383 Item Power",
            "70 All Resist (-2.2% Toughness)",
            "+19 Strength +[18 - 20]",
            "+8 Maximum Life [8 - 10]",
            "+1 Faith On Kill +[1]",
            "+10.1% Movement Speed [6.6 - 11.6]%",
            "Hunger: 10% increased chance for Rampage Items during Kill Streaks [10]%",
            "Your Disciple Skills with Cooldowns generate up to 30 Faith based on how far your travel with them.",
            "Requires Level 34. Lord of Hatred Item",
            "Unlocks new Aspect in the Codex of Power on salvage",
            "Sell Value: 9,284 Gold",
            "Tempers: 3/3",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(
                    max_value=20.0,
                    min_value=18.0,
                    name="strength",
                    text="+19 Strength +[18 - 20]",
                    type=AffixType.normal,
                    value=19.0,
                ),
                Affix(
                    max_value=10.0,
                    min_value=8.0,
                    name="maximum_life",
                    text="+8 Maximum Life [8 - 10]",
                    type=AffixType.normal,
                    value=8.0,
                ),
                Affix(
                    max_value=1.0,
                    min_value=1.0,
                    name="faith_on_kill",
                    text="+1 Faith On Kill +[1]",
                    type=AffixType.normal,
                    value=1.0,
                ),
                Affix(
                    max_value=11.6,
                    min_value=6.6,
                    name="movement_speed",
                    text="+10.1% Movement Speed [6.6 - 11.6]%",
                    type=AffixType.normal,
                    value=10.1,
                ),
            ],
            aspect=Aspect(
                name="of_pilgrims_progress",
                text="Your Disciple Skills with Cooldowns generate up to 30 Faith based on how far your travel with them.",
            ),
            codex_upgrade=True,
            cosmetic_upgrade=False,
            inherent=[],
            is_in_shop=False,
            item_type=ItemType.Amulet,
            name="inimical_seal_of_pilgrims_progress",
            original_name="INIMICAL SEAL OF PILGRIMS PROGRESS",
            power=383,
            rarity=ItemRarity.Legendary,
            seasonal_attribute=SeasonalAttribute.bloodied,
        ),
    ),
    (
        [
            "LURKING SNARE",
            "Bloodied Rare Gloves",
            "393 Item Power",
            "295 Armor (+1.6% Toughness)",
            "+24 Strength +[24 - 26]",
            "+9 Maximum Life [8 - 10]",
            "2.5% Resource Cost Reduction [2.2 - 2.5]%",
            "Rampage: +8% Critical Strike Chance per Kill Streak Tier [8]%",
            "Requires Level 38",
            "Sell Value: 2,775 Gold",
            "Durability: 100/100. Tempers: 1/1",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(
                    max_value=26.0,
                    min_value=24.0,
                    name="strength",
                    text="+24 Strength +[24 - 26]",
                    type=AffixType.normal,
                    value=24.0,
                ),
                Affix(
                    max_value=10.0,
                    min_value=8.0,
                    name="maximum_life",
                    text="+9 Maximum Life [8 - 10]",
                    type=AffixType.normal,
                    value=9.0,
                ),
                Affix(
                    max_value=2.5,
                    min_value=2.2,
                    name="resource_cost_reduction",
                    text="2.5% Resource Cost Reduction [2.2 - 2.5]%",
                    type=AffixType.normal,
                    value=2.5,
                ),
            ],
            aspect=None,
            codex_upgrade=False,
            cosmetic_upgrade=False,
            inherent=[],
            is_in_shop=False,
            item_type=ItemType.Gloves,
            name="lurking_snare",
            original_name="LURKING SNARE",
            power=393,
            rarity=ItemRarity.Rare,
            seasonal_attribute=SeasonalAttribute.bloodied,
        ),
    ),
]


@pytest.mark.parametrize(("input_item", "expected_item"), items)
def test_items(input_item: list[str], expected_item: Item):
    src.tts.LAST_ITEM = input_item
    item = read_descr()
    assert item == expected_item
