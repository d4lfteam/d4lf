import logging
import time
from typing import TYPE_CHECKING

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
    if is_non_sigil_mapping(item_descr.item_type):
        LOGGER.info("Matched: Non-sigil Mapping")
        return True
    if item_descr.item_type == ItemType.EscalationSigil and IniConfigLoader().general.ignore_escalation_sigils:
        LOGGER.info("Matched: Escalation Sigil and configured to be ignored")
        return True
    if is_socketable(item_descr.item_type):
        LOGGER.info("Matched: Socketable")
        return True
    if item_descr.item_type == ItemType.Material:
        LOGGER.info("Matched: Material")
        return True
    if item_descr.item_type == ItemType.Cache:
        LOGGER.info("Matched: Cache")
        return True
    if item_descr.item_type == ItemType.Cosmetic:
        LOGGER.info("Matched: Cosmetic only item")
        return True
    if item_descr.item_type == ItemType.LairBossKey:
        LOGGER.info("Matched: Lair Boss Key")
        return True
    if item_descr.sanctified:
        LOGGER.info("Matched: Sanctified item, which is not supported")
        return True

    return False


def is_junk_rarity(item_rarity: ItemRarity) -> bool:
    if IniConfigLoader().general.junk_rares:
        return item_rarity in [ItemRarity.Common, ItemRarity.Magic, ItemRarity.Rare]
    return item_rarity in [ItemRarity.Common, ItemRarity.Magic]


def correct_name(name: str) -> str | None:
    if name:
        return name.lower().replace("'", "").replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")
    return name
