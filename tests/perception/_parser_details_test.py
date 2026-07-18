from src.item import ItemRarity, ItemType
from src.perception._parser_details import _get_item_rarity, _get_item_type


def test_parser_details_maps_rarity_and_item_type_labels() -> None:
    assert _get_item_rarity("legendary") is ItemRarity.Legendary
    assert _get_item_type("sword") is ItemType.Sword
