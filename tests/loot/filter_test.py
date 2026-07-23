import logging
import typing
from types import SimpleNamespace

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

from src.item import Affix, AffixType, FilterResult, Item, ItemRarity, ItemType, MatchedFilter
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


def test_skipped_items_trigger_no_actions_or_filter_statistics(monkeypatch, mocker: MockerFixture, caplog):
    inventory = mocker.Mock()
    slots = [SimpleNamespace(is_junk=False, is_fav=False) for _ in range(3)]
    inventory.get_item_slots.return_value = (slots, [])
    inventory.menu_name = "inventory"
    item = Item(item_type=ItemType.Helm, power=900, affixes=[Affix(name="armor", type=AffixType.greater)])
    monkeypatch.setattr(_filter.src.perception, "read_latest_item", lambda: item)
    monkeypatch.setattr(_filter, "capture", lambda: object())
    monkeypatch.setattr(_filter.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(_filter, "is_ignored_item", lambda _item: False)
    monkeypatch.setattr(
        _filter, "Filter", lambda: SimpleNamespace(should_keep=lambda _item: FilterResult(False, [], True))
    )
    actions = [
        mocker.patch.object(_filter, name) for name in ("mark_as_favorite", "mark_as_junk", "drop_item_from_inventory")
    ]

    with caplog.at_level(logging.WARNING, logger=_filter.LOGGER.name):
        check_items(inventory, ItemRefreshType.no_refresh)

    for action in actions:
        action.assert_not_called()
    assert "all greater affixes" not in caplog.text


def test_mythic_keep_still_favorites_when_filter_category_is_disabled(monkeypatch, mocker: MockerFixture):
    inventory = mocker.Mock()
    inventory.get_item_slots.return_value = ([SimpleNamespace(is_junk=False, is_fav=False)], [])
    inventory.menu_name = "inventory"
    item = Item(item_type=ItemType.Helm, power=900, rarity=ItemRarity.Mythic)
    settings = SimpleNamespace(
        general=SimpleNamespace(
            filter_equipment=False,
            mark_as_favorite=True,
            do_not_junk_ancestral_legendaries=False,
            auto_use_temper_manuals=False,
        )
    )
    monkeypatch.setattr(_filter, "get_settings", lambda: settings)
    monkeypatch.setattr(_filter.src.perception, "read_latest_item", lambda: item)
    monkeypatch.setattr(_filter, "capture", lambda: object())
    monkeypatch.setattr(_filter.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(_filter, "is_ignored_item", lambda _item: False)
    monkeypatch.setattr(
        _filter,
        "Filter",
        lambda: SimpleNamespace(should_keep=lambda _item: FilterResult(True, [MatchedFilter("Mythics always kept")])),
    )
    favorite = mocker.patch.object(_filter, "mark_as_favorite")

    check_items(inventory, ItemRefreshType.no_refresh)

    favorite.assert_called_once_with()
