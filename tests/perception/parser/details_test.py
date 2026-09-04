from src.game_data import GameCatalog, ItemRarity, ItemType
from src.perception.parser.details import _get_item_rarity, _get_item_type


def test_parser_details_maps_rarity_and_item_type_labels() -> None:
    assert _get_item_rarity("legendary") is ItemRarity.Legendary
    assert _get_item_type("sword") is ItemType.Sword


def test_parser_details_accepts_item_type_enum_names_and_catalog_labels(monkeypatch) -> None:
    catalog = GameCatalog()
    monkeypatch.setattr(catalog, "item_types_dict", {**catalog.item_types_dict, "Incense": "Encens"})

    assert _get_item_type("Incense") is ItemType.Incense
    assert _get_item_type("incense") is ItemType.Incense
    assert _get_item_type("Encens") is ItemType.Incense
