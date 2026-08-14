from src.game_data import ItemType, is_armor, is_weapon


def test_item_type_helpers_use_catalog_metadata() -> None:
    assert is_armor(ItemType.Helm)
    assert is_weapon(ItemType.Sword)
    assert not is_weapon(ItemType.Ring)
