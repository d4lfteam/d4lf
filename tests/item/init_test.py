from src.game_data import ItemRarity, ItemType
from src.item import Affix, AffixType, FilterResult, Item, SeasonalAttribute


def test_public_item_exports_are_available() -> None:
    assert Affix(name="armor").type is AffixType.normal
    assert Item(item_type=ItemType.Helm).rarity is None
    assert ItemRarity.Rare.value == "rare"
    assert SeasonalAttribute.bloodied.value == "bloodied"
    assert FilterResult(keep=True, matched=[]).keep
