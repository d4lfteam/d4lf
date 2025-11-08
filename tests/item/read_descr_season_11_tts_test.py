import pytest

import src.tts
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr_tts import read_descr
from src.item.models import Item

items = [
    (
        # Sanctified items intentionally do not have their affixes read, which we are confirming with these next two tests
        [
            "ARCHON GAUNTLETS OF INFESTATION",
            "Ancestral Legendary Gloves",
            "800 Item Power",
            "[PH] 20 (+20) Quality",
            "Sanctified",
            "905 Armor",
            "+118 Dexterity +[107 - 121]",
            "+342 Life On Kill",
            "+97.5% Overpower Damage",
            "+451 Fire Resistance [441 - 490]",
            "+54 All Stats +[51 - 65]",
            "Lucky Hit: Centipede Skills have up to a 35% chance to spawn a Pestilent Swarm from the target which deals 436 [228 - 488] Poison damage per hit.. Pestilent Swarms now also deal 100% of their Base damage as Poisoning damage over 6 seconds.",
            "+14.2% Critical Strike Damage [12.0 - 15.0]%",
            "Requires Level 60. Account Bound. Vessel of Hatred Item",
            "Unmodifiable",
            "Sell Value: 19,254 Gold",
            "Durability: 100/100",
            "Right mouse button",
        ],
        Item(
            affixes=[],
            aspect=None,
            codex_upgrade=False,
            cosmetic_upgrade=False,
            inherent=[],
            is_chaos=False,
            is_in_shop=False,
            item_type=ItemType.Gloves,
            name="archon_gauntlets_of_infestation",
            power=800,
            rarity=ItemRarity.Legendary,
            sanctified=True,
        ),
    ),
    (
        [
            "ASCENDANT QUARTERSTAFF OF UNYIELDING HITS",
            "Ancestral Legendary Quarterstaff",
            "800 Item Power",
            "Sanctified",
            "596 Damage Per Second",
            "[434 - 650] Damage per Hit",
            "1.10 Attacks per Second (Fast)",
            "45% Block Chance [45]%",
            "+231 Dexterity +[214 - 242]",
            "+1,370 Maximum Life",
            "+292 Life On Hit [292 - 318]",
            "+114.0% Overpower Damage [110.0 - 130.0]%",
            "Ignore Durability Loss",
            "Casting a Gorilla Skill increases your Weapon Damage by 52% [20 - 60]% of your Armor for 3 seconds. Maximum 1,500 bonus Weapon Damage.",
            "Empty Socket",
            "Requires Level 60. Account Bound. Only. Vessel of Hatred Item",
            "Unmodifiable",
            "Sell Value: 52,949 Gold",
            "Durability: Indestructible",
            "Mousewheel scroll down",
            "Scroll Down",
            "Right mouse button",
        ],
        Item(
            affixes=[],
            aspect=None,
            codex_upgrade=False,
            cosmetic_upgrade=False,
            inherent=[],
            is_chaos=False,
            is_in_shop=False,
            item_type=ItemType.Quarterstaff,
            name="ascendant_quarterstaff_of_unyielding_hits",
            power=800,
            rarity=ItemRarity.Legendary,
            sanctified=True,
        ),
    ),
]


@pytest.mark.parametrize(("input_item", "expected_item"), items)
def test_items(input_item: list[str], expected_item: Item):
    src.tts.LAST_ITEM = input_item
    item = read_descr()
    assert item == expected_item
