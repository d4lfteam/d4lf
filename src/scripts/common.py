import logging
import sys
import time
from typing import TYPE_CHECKING

if sys.platform != "darwin":
    import keyboard

from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.item.data.item_type import ItemType, is_consumable, is_non_sigil_mapping, is_socketable
from src.item.data.rarity import ItemRarity
from src.utils.custom_mouse import mouse

if TYPE_CHECKING:
    from src.item.models import Item

LOGGER = logging.getLogger(__name__)

SETUP_INSTRUCTIONS_URL = "https://github.com/d4lfteam/d4lf/blob/main/README.md#how-to-setup"

COLOR_GREEN = "#23fc5d"  # Matched a profile
COLOR_RED = "#fc2323"  # Matched no profiles at all
COLOR_ORANGE = "#fca503"  # Matched a codex upgrade
COLOR_GREY = "#888888"  # Still processing or can't find the info we expect
COLOR_BLUE = "#00b3b3"  # We recognize this as an item, but it is not one we handle

ASPECT_UPGRADES_LABEL = "AspectUpgrades"


def mark_as_junk():
    keyboard.send("space")
    time.sleep(0.13)


def mark_as_favorite():
    LOGGER.info("Mark as favorite")
    keyboard.send("space")
    time.sleep(0.17)
    keyboard.send("space")
    time.sleep(0.13)


def drop_item_from_inventory() -> None:
    """Drop the currently-hovered inventory item (Ctrl + Left Click in-game)."""
    if keyboard is None:
        return
    keyboard.press("ctrl")
    time.sleep(0.03)
    mouse.click("left")
    time.sleep(0.03)
    keyboard.release("ctrl")
    time.sleep(0.10)


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
        LOGGER.info(f"{item_descr.original_name} -- Matched: Consumable")
        return True
    if is_non_sigil_mapping(item_descr.item_type):
        LOGGER.info(f"{item_descr.original_name} -- Matched: Non-sigil Mapping")
        return True
    if item_descr.item_type == ItemType.EscalationSigil and IniConfigLoader().general.ignore_escalation_sigils:
        LOGGER.info(f"{item_descr.original_name} -- Matched: Escalation Sigil and configured to be ignored")
        return True
    if is_socketable(item_descr.item_type):
        LOGGER.info(f"{item_descr.original_name} -- Matched: Socketable")
        return True
    if item_descr.item_type == ItemType.Material:
        LOGGER.info(f"{item_descr.original_name} -- Matched: Material")
        return True
    if item_descr.item_type == ItemType.Cache:
        LOGGER.info(f"{item_descr.original_name} -- Matched: Cache")
        return True
    if item_descr.item_type == ItemType.Cosmetic:
        LOGGER.info(f"{item_descr.original_name} -- Matched: Cosmetic only item")
        return True
    if item_descr.item_type == ItemType.LairBossKey:
        LOGGER.info(f"{item_descr.original_name} -- Matched: Lair Boss Key")
        return True
    if item_descr.sanctified:
        LOGGER.info(f"{item_descr.original_name} -- Matched: Sanctified item, which is not supported")
        return True

    return False


def is_junk_rarity(item_rarity: ItemRarity) -> bool:
    if IniConfigLoader().general.junk_rares:
        return item_rarity in [ItemRarity.Common, ItemRarity.Magic, ItemRarity.Rare]
    return item_rarity in [ItemRarity.Common, ItemRarity.Magic]
