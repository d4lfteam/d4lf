from src.item.data.affix import Affix, AffixType
from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.models import Item


class TestUnique(Item):
    def __init__(self, rarity=ItemRarity.Unique, item_type: ItemType = ItemType.Shield, power=910, **kwargs):
        super().__init__(rarity=rarity, item_type=item_type, power=power, **kwargs)


aspect_only_mythic_tests = [
    ("matches filter", True, ["aspect_only.tibaults_will"], TestUnique(aspect=Aspect(name="tibaults_will"), power=925)),
    ("does not match filter", False, [], TestUnique(aspect=Aspect(name="tibaults_will"), power=800)),
    ("matches with alias", True, ["alias_test.black_river"], TestUnique(aspect=Aspect(name="black_river"), power=925)),
    ("no aspect applies", True, [], TestUnique(aspect=Aspect("crown_of_lucion"))),
]

simple_mythics = [
    ("matches filter", True, TestUnique(aspect=Aspect(name="black_river"), power=925, rarity=ItemRarity.Mythic)),
    (
        "does not match but should keep",
        True,
        TestUnique(aspect=Aspect(name="black_river"), power=800, rarity=ItemRarity.Mythic),
    ),
]

global_uniques = [
    (
        "item power too low",
        [],
        TestUnique(power=800, aspect=Aspect(name="penitent_greaves", value=10, min_value=9, max_value=100)),
    ),
    (
        "has greater affixes",
        ["test.lidless_wall"],
        TestUnique(
            aspect=Aspect(name="lidless_wall", value=22, min_value=20, max_value=300),
            affixes=[
                Affix(name="attack_speed", value=9.6, type=AffixType.greater),
                Affix(name="lucky_hit_up_to_a_chance_to_restore_primary_resource", value=13.5, type=AffixType.greater),
                Affix(name="maximum_life", value=1111),
                Affix(name="maximum_essence", value=13),
            ],
            power=800,
        ),
    ),
    (
        "percent of affix is good",
        ["good_stuff.black_river"],
        TestUnique(aspect=Aspect(name="black_river", value=128, min_value=1, max_value=130), power=800),
    ),
]

uniques_with_affixes = [
    ("matches nothing", [], TestUnique(item_type=ItemType.Amulet, aspect=Aspect(name="dolmen_stone"))),
    ("unique aspect missing", [], TestUnique(item_type=ItemType.Helm, affixes=[Affix(name="maximum_life", value=641)])),
    (
        "matches aspect value",
        ["test.Helm"],
        TestUnique(
            item_type=ItemType.Helm,
            aspect=Aspect(name="crown_of_lucion", value=13),
            affixes=[Affix(name="maximum_life", value=641)],
        ),
    ),
    (
        "does not match aspect value",
        [],
        TestUnique(
            item_type=ItemType.Helm,
            aspect=Aspect(name="crown_of_lucion", value=10),
            affixes=[Affix(name="maximum_life", value=5)],
        ),
    ),
    (
        "percent affix/aspect pass",
        ["test.PercentBoots"],
        TestUnique(
            item_type=ItemType.Boots,
            affixes=[
                Affix(name="movement_speed", value=9.0, min_value=5.0, max_value=10.0),
                Affix(name="dodge_chance", value=3.0),
            ],
            aspect=Aspect(name="penitent_greaves", value=10, min_value=1, max_value=11),
        ),
    ),
    (
        "percent affix pass but aspect fail",
        [],
        TestUnique(
            item_type=ItemType.Boots,
            affixes=[
                Affix(name="movement_speed", value=9.0, min_value=5.0, max_value=10.0),
                Affix(name="dodge_chance", value=3.0),
            ],
            aspect=Aspect(name="penitent_greaves", value=2, min_value=1, max_value=11),
        ),
    ),
    (
        "greater affix",
        ["test.CountBoots", "test.UniqueAspectWithGA"],
        TestUnique(
            item_type=ItemType.Boots,
            affixes=[
                Affix(name="movement_speed", value=4, type=AffixType.greater),
                Affix(name="intelligence", value=4, type=AffixType.greater),
                Affix(name="maximum_life", value=4),
                Affix(name="shadow_resistance", value=4),
            ],
            aspect=Aspect(name="flickerstep"),
        ),
    ),
    (
        "greater affix but aspect is wrong",
        [],
        TestUnique(
            item_type=ItemType.Boots,
            affixes=[
                Affix(name="movement_speed", value=4, type=AffixType.greater),
                Affix(name="intelligence", value=4, type=AffixType.greater),
                Affix(name="maximum_life", value=4),
                Affix(name="shadow_resistance", value=4),
            ],
            aspect=Aspect(name="blood_wake"),
        ),
    ),
    ("aspect only", ["test.UniqueAspectOnly"], TestUnique(aspect=Aspect(name="battle_trance"))),
    (
        "smaller aspect value",
        ["test.SmallerUniqueAspectValue"],
        TestUnique(aspect=Aspect(name="crown_of_lucion", value=10, min_value=15, max_value=10)),
    ),
]
