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
        # The next 2 tests are bloodied items
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
                Affix(
                    max_value=10.0,
                    min_value=10.0,
                    name="hunger_increased_chance_for_rampage_items_during_kill_streaks",
                    text="Hunger: 10% increased chance for Rampage Items during Kill Streaks [10]%",
                    type=AffixType.normal,
                    value=10.0,
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
                Affix(
                    max_value=8.0,
                    min_value=8.0,
                    name="rampage_critical_strike_chance_per_kill_streak_tier",
                    text="Rampage: +8% Critical Strike Chance per Kill Streak Tier [8]%",
                    type=AffixType.normal,
                    value=8.0,
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
    # New DOOM cosmetics are just regular uniques with the word crucible in them. We remove the word and treat as normal uniques
    (
        [
            "SHARD OF VERATHIEL (CRUCIBLE)",
            "Ancestral Unique Sword",
            "800 Item Power",
            "Crucible Cosmetic Variant",
            "298 Damage Per Second (+283)",
            "[217 - 325] Damage per Hit",
            "1.10 Attacks per Second (Fast)",
            "+50.0% Damage [50.0]%",
            "+58 All Stats +[51 - 65]",
            "+24 Maximum Resource",
            "+18.0% Basic Attack Speed [16.0 - 25.0]%",
            "+2 to Basic Skills [1 - 2]",
            "Basic Skills deal 115%[x] [50 - 150]% increased damage but additionally cost 25 Primary Resource.",
            "Empty Socket",
            "This blade once bore divine purpose wielded by the angel Verathiel. Like its keeper, the sword fell to Infernal depths. Yet beneath this corruption, is a heartbeat of a past memory, holding steadfast.",
            "Requires Level 60. Account Bound. Unique Equipped",
            "Unlocks new look on salvage",
            "Sell Value: 117,933 Gold",
            "Durability: 100/100",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(
                    max_value=65.0,
                    min_value=51.0,
                    name="all_stats",
                    text="+58 All Stats +[51 - 65]",
                    type=AffixType.normal,
                    value=58.0,
                ),
                Affix(
                    max_value=None,
                    min_value=None,
                    name="maximum_resource",
                    text="+24 Maximum Resource",
                    type=AffixType.greater,
                    value=24.0,
                ),
                Affix(
                    max_value=25.0,
                    min_value=16.0,
                    name="basic_attack_speed",
                    text="+18.0% Basic Attack Speed [16.0 - 25.0]%",
                    type=AffixType.normal,
                    value=18.0,
                ),
                Affix(
                    max_value=2.0,
                    min_value=1.0,
                    name="to_basic_skills",
                    text="+2 to Basic Skills [1 - 2]",
                    type=AffixType.normal,
                    value=2.0,
                ),
            ],
            aspect=Aspect(
                name="shard_of_verathiel",
                min_value=50.0,
                max_value=150.0,
                text="Basic Skills deal 115%[x] [50 - 150]% increased damage but additionally cost 25 Primary Resource.",
                value=115.0,
            ),
            codex_upgrade=False,
            cosmetic_upgrade=True,
            inherent=[
                Affix(
                    max_value=50.0,
                    min_value=50.0,
                    name="damage",
                    text="+50.0% Damage [50.0]%",
                    type=AffixType.inherent,
                    value=50.0,
                )
            ],
            is_in_shop=False,
            item_type=ItemType.Sword,
            name="shard_of_verathiel",
            original_name="SHARD OF VERATHIEL (CRUCIBLE)",
            power=800,
            rarity=ItemRarity.Unique,
            seasonal_attribute=None,
        ),
    ),
    # Bloodied nightmare sigil
    (
        [
            "ULDURS CAVE NIGHTMARE SIGIL",
            "Bloodied Nightmare Sigil",
            "Transform this place into a  Bloodied Nightmare Dungeon with greater challenge and greater reward.",
            "Uldurs Cave in Kehjistan",
            "DUNGEON AFFIXES",
            "Obols Reserve",
            "Many Obols chests have been stashed here.",
            "Profane Aegis",
            "Monsters gain 50% of their Maximum Life as a Barrier.",
            "Bloodstained",
            "Enemies are much stronger here.",
            "Relentless Butcher",
            "The Butcher is relentlessly stalking you...",
            "Account Bound",
            "Seasonal Item",
            "Sell Value: 1 Gold",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(max_value=None, min_value=None, name="obols_reserve", text="", type=AffixType.normal, value=None),
                Affix(max_value=None, min_value=None, name="profane_aegis", text="", type=AffixType.normal, value=None),
            ],
            aspect=None,
            codex_upgrade=False,
            cosmetic_upgrade=False,
            inherent=[],
            is_in_shop=False,
            item_type=ItemType.Sigil,
            name="uldurs_cave",
            original_name="ULDURS CAVE NIGHTMARE SIGIL",
            power=None,
            rarity=ItemRarity.Common,
            seasonal_attribute=SeasonalAttribute.bloodied,
        ),
    ),
]


@pytest.mark.parametrize(("input_item", "expected_item"), items)
def test_items(input_item: list[str], expected_item: Item):
    src.tts.LAST_ITEM = input_item
    item = read_descr()
    assert item == expected_item
