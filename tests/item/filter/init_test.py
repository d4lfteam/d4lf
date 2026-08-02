from src.game_data import ItemType
from src.item import Item
from src.item.filter import Filter


def test_filter_package_exposes_keep_decisions_through_the_item_facade() -> None:
    result = Filter().should_keep(Item(item_type=ItemType.Helm))
    assert result.keep is False
    assert result.matched == []
