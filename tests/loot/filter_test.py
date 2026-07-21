import typing

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

from src.loot import filter as _filter
from src.loot.filter import check_items
from src.settings import ItemRefreshType


def test_force_without_filter_only_refreshes_item_status(monkeypatch, mocker: MockerFixture):
    inventory = mocker.Mock()
    inventory.get_item_slots.return_value = ([], [])
    reset = mocker.Mock()
    monkeypatch.setattr(_filter, "reset_item_status", reset)

    check_items(inventory, ItemRefreshType.force_without_filter)

    reset.assert_called_once_with([], inventory)
    inventory.hover_item_with_delay.assert_not_called()
