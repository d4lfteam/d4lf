from src.item.data.affix import AffixType
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.parse_affixes import (
    add_affixes_from_tts,
    get_affix_counts,
    get_affix_from_text,
)
from src.item.models import Item


class DummyDataLoader:
    def __init__(self, affix_dict=None, aspect_unique_dict=None):
        self.affix_dict = affix_dict or {}
        self.aspect_unique_dict = aspect_unique_dict or {}


def test_get_affix_counts_handles_boots_shield_and_unique_inherents():
    boots = Item(item_type=ItemType.Boots, rarity=ItemRarity.Rare)
    shield = Item(item_type=ItemType.Shield, rarity=ItemRarity.Legendary)
    unique = Item(item_type=ItemType.Shield, rarity=ItemRarity.Unique, name="black_river")
    loader = DummyDataLoader(aspect_unique_dict={"black_river": {"num_inherents": 2}})

    assert get_affix_counts(["a", "b", "c", "d", "Empty Socket"], boots, 0, dataloader=loader) == (1, 3)
    assert get_affix_counts(["a", "b", "c", "d", "e", "f", "g"], shield, 0, dataloader=loader) == (3, 4)
    assert get_affix_counts(["a", "b", "c", "d", "e", "f"], unique, 0, dataloader=loader) == (2, 4)


def test_get_affix_from_text_parses_normal_and_greater_affixes():
    loader = DummyDataLoader(
        affix_dict={
            "movement_speed": None,
            "maximum_resource": None,
        }
    )

    normal = get_affix_from_text("+10.0% Movement Speed [6.6 - 11.6]%", dataloader=loader)
    greater = get_affix_from_text("+24 Maximum Resource", dataloader=loader)

    assert normal.name == "movement_speed"
    assert normal.type == AffixType.normal
    assert normal.value == 10.0
    assert normal.min_value == 6.6
    assert normal.max_value == 11.6
    assert greater.name == "maximum_resource"
    assert greater.type == AffixType.greater
    assert greater.value == 24.0


def test_add_affixes_from_tts_populates_inherent_and_regular_affixes():
    item = Item(item_type=ItemType.Boots, rarity=ItemRarity.Rare)
    tts_section = [
        "TITLE",
        "+10.0% Movement Speed [6.6 - 11.6]%",
        "+24 Maximum Resource",
        "+9 Maximum Life [8 - 10]",
        "+3 Dexterity [1 - 4]",
        "+7 Intelligence [5 - 8]",
    ]
    loader = DummyDataLoader(
        affix_dict={
            "movement_speed": None,
            "maximum_resource": None,
            "maximum_life": None,
            "dexterity": None,
            "intelligence": None,
        }
    )

    result = add_affixes_from_tts(
        tts_section,
        item,
        dataloader=loader,
        parse_aspect_func=lambda *_args, **_kwargs: None,
    )

    assert result is item
    assert [affix.name for affix in item.inherent] == ["movement_speed"]
    assert [affix.name for affix in item.affixes] == [
        "maximum_resource",
        "maximum_life",
        "dexterity",
        "intelligence",
    ]
    assert item.aspect is None
