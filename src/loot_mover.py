import logging

from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import MoveItemsType
from src.ui.char_inventory import CharInventory
from src.ui.chest import Chest
from src.ui.inventory_base import ItemSlot
from src.utils.custom_mouse import mouse

LOGGER = logging.getLogger(__name__)


def move_items_to_stash():
    LOGGER.info("Move inventory items to stash")

    inv = CharInventory()
    chest = Chest()

    if not chest.is_open():
        LOGGER.error("Moving items only works if stash is open")
        return

    unhandled_slots, _ = inv.get_item_slots()
    move_item_types = IniConfigLoader().general.move_to_stash_item_type
    if not unhandled_slots:
        LOGGER.info("No items to move")
        return

    for i in IniConfigLoader().general.check_chest_tabs:
        chest.switch_to_tab(i)

        _, empty_chest = chest.get_item_slots()

        if not empty_chest:
            continue

        _, unhandled_slots = _move_items(inv, unhandled_slots, len(empty_chest), move_item_types)

        if not unhandled_slots:
            break

    mouse.move(*Cam().abs_window_to_monitor((0, 0)))
    LOGGER.info("Completed move")


def move_items_to_inventory():
    LOGGER.info("Move stash items to inventory")

    inv = CharInventory()
    chest = Chest()

    if not chest.is_open():
        LOGGER.error("Moving items only works if stash is open")
        return

    _, empty_inv = inv.get_item_slots()
    empty_slot_count = len(empty_inv)
    move_item_type = IniConfigLoader().general.move_to_inv_item_type
    if not empty_slot_count:
        LOGGER.info("No empty slots in inventory")
        return

    for i in IniConfigLoader().general.check_chest_tabs:
        chest.switch_to_tab(i)
        unhandled_slots, _ = chest.get_item_slots()

        LOGGER.debug(
            f"Stash tab {i} - Number of stash items: {len(unhandled_slots)} - Number of empty inventory spaces: {empty_slot_count}"
        )

        item_move_count, _ = _move_items(inv, unhandled_slots, empty_slot_count, move_item_type)
        empty_slot_count = empty_slot_count - item_move_count
        LOGGER.debug(f"Moved {item_move_count} items, now have {empty_slot_count} empty slots left.")

        if empty_slot_count < 1:
            break

    mouse.move(*Cam().abs_window_to_monitor((0, 0)))
    LOGGER.info("Completed move")


def _move_items(
    inv: CharInventory, occupied: list[ItemSlot], num_to_move: int, move_item_types: list[MoveItemsType]
) -> tuple[int, list[ItemSlot]]:
    """
    Handles actually moving items to or from the stash, based on a parameter
    :param inv: The Inventory object, used for hovering over the item
    :param occupied: The ItemSlot list of occupied items to move
    :param num_to_move: The maximum number of items to move
    :return: A tuple of the number of items that were moved and a list of unhandled occupied ItemSlots
    """
    item_move_count = 0
    remaining_unhandled_slots = occupied.copy()
    for item in occupied:
        remaining_unhandled_slots.remove(item)

        if (
            (MoveItemsType.favorites in move_item_types and item.is_fav)
            or (MoveItemsType.junk in move_item_types and item.is_junk)
            or (MoveItemsType.unmarked in move_item_types and not item.is_fav and not item.is_junk)
            or MoveItemsType.everything in move_item_types
        ):
            inv.hover_item(item)
            mouse.click("right")
            item_move_count = item_move_count + 1

        if item_move_count == num_to_move:
            break

    return item_move_count, remaining_unhandled_slots
