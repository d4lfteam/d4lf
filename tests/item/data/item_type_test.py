from src.item.data.item_type import (
    ItemType,
    is_armor,
    is_consumable,
    is_jewelry,
    is_non_sigil_mapping,
    is_seal_or_charm,
    is_sigil,
    is_socketable,
    is_weapon,
)


def test_item_type_categories():
    assert is_armor(ItemType.Helm)
    assert is_consumable(ItemType.Elixir)
    assert is_jewelry(ItemType.Ring)
    assert is_non_sigil_mapping(ItemType.Compass)
    assert is_seal_or_charm(ItemType.Charm)
    assert is_sigil(ItemType.Sigil)
    assert is_socketable(ItemType.Gem)
    assert is_weapon(ItemType.Sword)
    assert not is_weapon(ItemType.Helm)
