from unittest.mock import Mock

from src.loot import _filter
from src.loot._filter import check_items
from src.settings import ItemRefreshType


def test_force_without_filter_only_refreshes_item_status(monkeypatch):
    inventory = Mock()
    inventory.get_item_slots.return_value = ([], [])
    reset = Mock()
    monkeypatch.setattr(_filter, "reset_item_status", reset)

    check_items(inventory, ItemRefreshType.force_without_filter)

    reset.assert_called_once_with([], inventory)
    inventory.hover_item_with_delay.assert_not_called()
