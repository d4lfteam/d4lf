from src.item.data.affix import Affix, AffixType
from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.models import Item

charms = [
    (
        "magic charm affix and rarity match",
        ["seal_charm.Charms.basic_magic"],
        Item(
            item_type=ItemType.Charm,
            name="skillful_charm",
            original_name="SKILLFUL CHARM",
            rarity=ItemRarity.Magic,
            affixes=[Affix(name="to_basic_skills", value=2.0, min_value=2.0, max_value=3.0)],
        ),
    ),
    (
        "rare charm affix and rarity match",
        ["seal_charm.Charms.speed"],
        Item(
            item_type=ItemType.Charm,
            name="speedy_charm_of_greed",
            original_name="SPEEDY CHARM OF GREED",
            rarity=ItemRarity.Rare,
            affixes=[
                Affix(name="gold_drop_rate", value=7.0, min_value=5.0, max_value=9.0),
                Affix(name="movement_speed", value=14.0, min_value=13.0, max_value=16.0),
            ],
        ),
    ),
    (
        "set name match",
        ["seal_charm.Charms.wanted_set"],
        Item(
            item_type=ItemType.Charm,
            name="mlor_of_sescherons_fury",
            original_name="MLOR OF SESCHERONS FURY",
            rarity=ItemRarity.Set,
            set="sescherons_fury",
            affixes=[
                Affix(name="maximum_life", value=8.0, min_value=6.5, max_value=8.0),
                Affix(name="lucky_hit_up_to_a_chance_to_daze_for_seconds", value=4.0, min_value=3.0, max_value=4.0),
            ],
        ),
    ),
    (
        "unique aspect name match",
        ["seal_charm.Charms.wanted_unique_aspect"],
        Item(
            item_type=ItemType.Charm,
            name="tuskhelm_of_joritz_the_mighty",
            original_name="TUSKHELM OF JORITZ THE MIGHTY",
            rarity=ItemRarity.Unique,
            aspect=Aspect(name="tuskhelm_of_joritz_the_mighty", value=48.0, min_value=40.0, max_value=50.0),
            set=None,
            affixes=[
                Affix(name="cold_resistance", value=486.0, min_value=416.0, max_value=523.0),
                Affix(
                    name="lucky_hit_up_to_a_chance_to_deal_physical_damage",
                    value=950.0,
                    min_value=550.0,
                    max_value=1000.0,
                ),
            ],
        ),
    ),
    (
        "wrong unique aspect rejected",
        [],
        Item(
            item_type=ItemType.Charm,
            name="tuskhelm_of_joritz_the_mighty",
            original_name="TUSKHELM OF JORITZ THE MIGHTY",
            rarity=ItemRarity.Unique,
            aspect=Aspect(name="flickerstep"),
            set=None,
            affixes=[Affix(name="cold_resistance", value=486.0, min_value=416.0, max_value=523.0)],
        ),
    ),
    (
        "rare charm against unique aspect filter rejected",
        [],
        Item(
            item_type=ItemType.Charm,
            name="speedy_charm_of_greed",
            original_name="SPEEDY CHARM OF GREED",
            rarity=ItemRarity.Rare,
            aspect=None,
            set=None,
            affixes=[Affix(name="gold_drop_rate", value=7.0, min_value=5.0, max_value=9.0)],
        ),
    ),
    (
        "wrong set rejected",
        [],
        Item(
            item_type=ItemType.Charm,
            name="fer_of_sescherons_fury",
            original_name="FER OF SESCHERONS FURY",
            rarity=ItemRarity.Set,
            set="cains_wild_lightning",
            affixes=[
                Affix(name="fire_resistance", value=166.0, min_value=165.0, max_value=210.0),
                Affix(name="to_combat_skills", value=2.0, min_value=1.0, max_value=2.0),
            ],
        ),
    ),
    (
        "no set rejected",
        [],
        Item(
            item_type=ItemType.Charm,
            name="skillful_charm",
            original_name="SKILLFUL CHARM",
            rarity=ItemRarity.Rare,
            set=None,
            affixes=[Affix(name="to_basic_skills", value=2.0, min_value=2.0, max_value=3.0)],
        ),
    ),
    (
        "mythic always kept",
        ["Mythic Charm"],
        Item(
            item_type=ItemType.Charm,
            name="tuskhelm_of_joritz_the_mighty",
            rarity=ItemRarity.Mythic,
            aspect=None,
            affixes=[Affix(name="cold_resistance", type=AffixType.greater)],
        ),
    ),
]
