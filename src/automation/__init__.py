"""Platform-neutral game automation interface."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src import settings as settings_module

from ._character_inventory import CharInventory
from ._contracts import Inventory, StashInventory
from ._inventory import ItemSlot
from ._loot_mover import move_items_to_inventory, move_items_to_stash
from ._mouse import Mouse
from ._process import kill_thread, safe_exit, set_process_name
from ._stash import Stash
from ._vendor import Vendor
from ._window import (
    WindowSpec,
    detect_window,
    find_and_set_window_position,
    get_window_spec_id,
    is_self_foreground,
    is_window_foreground,
    move_window_to_foreground,
    start_detecting_window,
    stop_detecting_window,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def character_inventory() -> Inventory:
    return CharInventory()


def stash_inventory() -> StashInventory:
    return Stash()


def vendor_inventory() -> Inventory:
    return Vendor()


def send_hotkey(value: str) -> None:
    settings_module.send(value)


def press_key(value: str) -> None:
    settings_module.press(value)


def release_key(value: str) -> None:
    settings_module.release(value)


def add_hotkey(hotkey: str, callback: Callable[[], None]) -> int:
    return settings_module.add_hotkey(hotkey, callback)


def remove_hotkey(handle: int) -> None:
    settings_module.remove_hotkey(handle)


move_pointer = Mouse.move
click_pointer = Mouse.click
pointer_position = Mouse.get_position

__all__ = [
    "Inventory",
    "ItemSlot",
    "StashInventory",
    "WindowSpec",
    "add_hotkey",
    "character_inventory",
    "click_pointer",
    "detect_window",
    "find_and_set_window_position",
    "get_window_spec_id",
    "is_self_foreground",
    "is_window_foreground",
    "kill_thread",
    "move_items_to_inventory",
    "move_items_to_stash",
    "move_pointer",
    "move_window_to_foreground",
    "pointer_position",
    "press_key",
    "release_key",
    "remove_hotkey",
    "safe_exit",
    "send_hotkey",
    "set_process_name",
    "start_detecting_window",
    "stash_inventory",
    "stop_detecting_window",
    "vendor_inventory",
]
