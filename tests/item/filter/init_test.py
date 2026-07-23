from src.item import Filter, Item, ItemType


def test_filter_package_exposes_keep_decisions_through_the_item_facade() -> None:
    result = Filter().should_keep(Item(item_type=ItemType.Helm))
    assert result.keep is False
    assert result.matched == []
