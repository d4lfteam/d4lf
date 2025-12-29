from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.models import Item


class TestItem(Item):
    def __init__(self, rarity=ItemRarity.Legendary, power=910, **kwargs):
        super().__init__(rarity=rarity, power=power, **kwargs)


affixes = [
    ("wrong type", [], TestItem(item_type=ItemType.Amulet)),
    ("power too low", [], TestItem(item_type=ItemType.Helm, power=724)),
    (
        "res boots 4 res",
        [],
        TestItem(
            item_type=ItemType.Boots,
            affixes=[
                Affix(name="cold_resistance", value=5),
                Affix(name="fire_resistance", value=5),
                Affix(name="poison_resistance", value=5),
                Affix(name="shadow_resistance", value=5),
            ],
        ),
    ),
    (
        "res boots 3 res",
        [],
        TestItem(
            item_type=ItemType.Boots,
            affixes=[
                Affix(name="cold_resistance", value=5),
                Affix(name="fire_resistance", value=5),
                Affix(name="shadow_resistance", value=5),
            ],
        ),
    ),
    (
        "res boots 3 res+ms",
        ["test.ResBoots"],
        TestItem(
            item_type=ItemType.Boots,
            affixes=[
                Affix(name="cold_resistance", value=5),
                Affix(name="movement_speed", value=5),
                Affix(name="fire_resistance", value=5),
                Affix(name="shadow_resistance", value=5),
            ],
        ),
    ),
    (
        "res boots 2 res",
        [],
        TestItem(
            item_type=ItemType.Boots,
            affixes=[Affix(name="cold_resistance", value=5), Affix(name="shadow_resistance", value=5)],
        ),
    ),
    (
        "res boots 2 res+ms",
        ["test.ResBoots"],
        TestItem(
            item_type=ItemType.Boots,
            affixes=[
                Affix(name="cold_resistance", value=5),
                Affix(name="movement_speed", value=5),
                Affix(name="shadow_resistance", value=5),
            ],
        ),
    ),
    (
        "helm life",
        [],
        TestItem(
            item_type=ItemType.Helm,
            affixes=[
                Affix(name="maximum_life", value=5),
                Affix(name="movement_speed", value=5),
                Affix(name="fire_resistance", value=5),
                Affix(name="shadow_resistance", value=5),
            ],
        ),
    ),
    (
        "boots inherent",
        ["test.GreatBoots", "test.ResBoots"],
        TestItem(
            item_type=ItemType.Boots,
            affixes=[
                Affix(name="movement_speed", value=5),
                Affix(name="cold_resistance", value=5),
                Affix(name="lightning_resistance", value=5),
            ],
            inherent=[Affix(name="maximum_evade_charges", value=5)],
        ),
    ),
    (
        "boots no inherent",
        ["test.ResBoots"],
        TestItem(
            item_type=ItemType.Boots,
            affixes=[
                Affix(name="movement_speed", value=5),
                Affix(name="cold_resistance", value=5),
                Affix(name="lightning_resistance", value=5),
            ],
            inherent=[Affix(name="maximum_fury", value=5)],
        ),
    ),
    (
        "boots exact values",
        ["test.ResBoots", "test.ResBootsExact"],
        TestItem(
            item_type=ItemType.Boots,
            affixes=[
                Affix(name="movement_speed", value=4),
                Affix(name="cold_resistance", value=4),
                Affix(name="lightning_resistance", value=4),
            ],
            inherent=[Affix(name="maximum_fury", value=5)],
        ),
    ),
    (
        "greater affix",
        ["test.GreaterAffixes"],
        TestItem(
            item_type=ItemType.Boots,
            affixes=[
                Affix(name="movement_speed", value=4, type=AffixType.greater),
                Affix(name="intelligence", value=4),
                Affix(name="maximum_life", value=4),
                Affix(name="shadow_resistance", value=4),
            ],
            inherent=[Affix(name="maximum_fury", value=5)],
        ),
    ),
    (
        "greater affix 2",
        ["test.CountBoots", "test.CountBootsMatch", "test.GreaterAffixes"],
        TestItem(
            item_type=ItemType.Boots,
            affixes=[
                Affix(name="movement_speed", value=4, type=AffixType.greater),
                Affix(name="intelligence", value=4, type=AffixType.greater),
                Affix(name="maximum_life", value=4),
                Affix(name="shadow_resistance", value=4),
            ],
            inherent=[Affix(name="maximum_fury", value=5)],
        ),
    ),
]
