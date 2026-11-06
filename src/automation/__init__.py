"""Platform-neutral game automation interface."""

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


def character_inventory() -> Inventory:
    return CharInventory()


def stash_inventory() -> StashInventory:
    return Stash()


def vendor_inventory() -> Inventory:
    return Vendor()


move_pointer = Mouse.move
click_pointer = Mouse.click
pointer_position = Mouse.get_position

__all__ = [
    "Inventory",
    "ItemSlot",
    "StashInventory",
    "WindowSpec",
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
    "safe_exit",
    "set_process_name",
    "start_detecting_window",
    "stash_inventory",
    "stop_detecting_window",
    "vendor_inventory",
]
