"""Platform-neutral game automation interface."""

from typing import TYPE_CHECKING

from src.automation.character import CharInventory
from src.automation.contracts import Inventory, StashInventory
from src.automation.inventory import ItemSlot
from src.automation.loot_mover import move_items_to_inventory, move_items_to_stash
from src.automation.mouse import Mouse
from src.automation.process import kill_thread, safe_exit, set_process_name
from src.automation.stash import Stash
from src.automation.vendor import Vendor
from src.automation.window import (
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
from src.settings import hotkeys as hotkeys_module

if TYPE_CHECKING:
    from collections.abc import Callable


def character_inventory() -> Inventory:
    return CharInventory()


def stash_inventory() -> StashInventory:
    return Stash()


def vendor_inventory() -> Inventory:
    return Vendor()


def send_hotkey(value: str) -> None:
    hotkeys_module.send(value)


def press_key(value: str) -> None:
    hotkeys_module.press(value)


def release_key(value: str) -> None:
    hotkeys_module.release(value)


def add_hotkey(hotkey: str, callback: Callable[[], None]) -> int:
    return hotkeys_module.add_hotkey(hotkey, callback)


def remove_hotkey(handle: int) -> None:
    hotkeys_module.remove_hotkey(handle)


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
