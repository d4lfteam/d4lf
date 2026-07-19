from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

from src import automation
from src.automation import loot_mover as _loot_mover
from src.automation.inventory import ItemSlot
from src.automation.loot_mover import _move_items
from src.settings import MoveItemsType


def test_move_items_returns_unhandled_slots_when_type_does_not_match(monkeypatch):
    inv = type("Inventory", (), {"hover_item": lambda *_: None})()
    slot = ItemSlot((0, 0, 1, 1), (0, 0))
    monkeypatch.setattr("src.automation.loot_mover.Mouse.click", lambda *_: None)
    moved, remaining = _move_items(cast("Any", inv), [slot], 1, [MoveItemsType.favorites])
    assert moved == 0
    assert remaining == []


def test_move_items_to_stash_requires_an_open_stash(monkeypatch):
    monkeypatch.setattr(_loot_mover, "CharInventory", Mock)
    stash = Mock(is_open=Mock(return_value=False))
    monkeypatch.setattr(_loot_mover, "Stash", lambda: stash)

    automation.move_items_to_stash()

    stash.get_item_slots.assert_not_called()


def test_move_items_to_stash_uses_configured_tabs_and_capacity(monkeypatch):
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
