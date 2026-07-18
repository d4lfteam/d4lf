from types import SimpleNamespace
from unittest.mock import Mock

from src import automation
from src.automation import _loot_mover
from src.settings import MoveItemsType


def test_move_items_to_stash_requires_an_open_stash(monkeypatch) -> None:
    monkeypatch.setattr(_loot_mover, "CharInventory", Mock)
    stash = Mock(is_open=Mock(return_value=False))
    monkeypatch.setattr(_loot_mover, "Stash", lambda: stash)

    automation.move_items_to_stash()

    stash.get_item_slots.assert_not_called()


def test_move_items_to_stash_uses_configured_tabs_and_capacity(monkeypatch) -> None:
    item = SimpleNamespace(is_fav=True, is_junk=False)
    inventory = Mock()
    inventory.get_item_slots.return_value = ([item], [])
    stash = Mock(is_open=Mock(return_value=True))
    stash.get_item_slots.return_value = ([], [object()])
    settings = SimpleNamespace(
        general=SimpleNamespace(move_to_stash_item_type=[MoveItemsType.favorites], check_chest_tabs=[2, 4])
    )
    monkeypatch.setattr(_loot_mover, "CharInventory", lambda: inventory)
    monkeypatch.setattr(_loot_mover, "Stash", lambda: stash)
    monkeypatch.setattr(_loot_mover, "get_settings", lambda: settings)
    monkeypatch.setattr(_loot_mover, "abs_window_to_monitor", lambda coordinate: coordinate)
    mouse = Mock()
    monkeypatch.setattr(_loot_mover, "Mouse", mouse)

    automation.move_items_to_stash()

    stash.switch_to_tab.assert_called_once_with(2)
    inventory.hover_item.assert_called_once_with(item)
    mouse.click.assert_called_once_with("right")
