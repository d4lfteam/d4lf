import logging
import time

import keyboard

from src.cam import Cam
from src.item.data.item_type import ItemType, is_consumable, is_mapping, is_socketable
from src.item.models import Item
from src.utils.custom_mouse import mouse

LOGGER = logging.getLogger(__name__)

SETUP_INSTRUCTIONS_URL = "https://github.com/d4lfteam/d4lf/blob/main/README.md#how-to-setup"


def mark_as_junk():
    keyboard.send("space")
    time.sleep(0.13)


def mark_as_favorite():
    LOGGER.info("Mark as favorite")
    keyboard.send("space")
    time.sleep(0.17)
    keyboard.send("space")
    time.sleep(0.13)


def reset_canvas(root, canvas):
    canvas.delete("all")
    canvas.config(height=0, width=0)
    root.geometry("0x0+0+0")
    root.update_idletasks()
    root.update()


def reset_item_status(occupied, inv):
    for item_slot in occupied:
        if item_slot.is_fav:
            inv.hover_item_with_delay(item_slot)
            keyboard.send("space")
        if item_slot.is_junk:
            inv.hover_item_with_delay(item_slot)
            keyboard.send("space")
            time.sleep(0.15)
            keyboard.send("space")
        time.sleep(0.15)

    if occupied:
        mouse.move(*Cam().abs_window_to_monitor((0, 0)))


def is_ignored_item(item_descr: Item):
    if is_consumable(item_descr.item_type):
        LOGGER.info("Matched: Consumable")
        return True
    if is_mapping(item_descr.item_type) and item_descr.item_type != ItemType.Sigil:
        LOGGER.info("Matched: Non-sigil Mapping")
        return True
    if is_socketable(item_descr.item_type):
        LOGGER.info("Matched: Socketable")
        return True
    if item_descr.item_type == ItemType.Material:
        LOGGER.info("Matched: Material")
        return True
    if item_descr.item_type == ItemType.TemperManual:
        LOGGER.info("Matched: Temper Manual")
        return True
    if item_descr.item_type == ItemType.Cache:
        LOGGER.info("Matched: Cache")
        return True

    return False
