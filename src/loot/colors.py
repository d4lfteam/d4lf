"""Loot-owned colors and item classification helpers."""

import logging
import time
from dataclasses import dataclass

from src import automation
from src.item import ItemType, SeasonalAttribute, is_consumable, is_non_sigil_mapping, is_socketable
from src.perception import abs_window_to_monitor
from src.settings import get_settings

LOGGER = logging.getLogger(__name__)
ACCENT_BLUE = "#56B4E9"


@dataclass(frozen=True, slots=True)
class FilterColors:
    matched: str
    no_match: str
    codex_upgrade: str
    processing: str
    unhandled: str


FILTER_COLORS_DEFAULT = FilterColors("#23fc5d", "#fc2323", "#fca503", "#888888", "#00b3b3")
FILTER_COLORS_COLORBLIND = FilterColors(ACCENT_BLUE, "#D55E00", "#E69F00", "#888888", "#CC79A7")


def get_filter_colors() -> FilterColors:
    try:
        return FILTER_COLORS_COLORBLIND if get_settings().general.colorblind_mode else FILTER_COLORS_DEFAULT
    except Exception:
        LOGGER.debug("Config unavailable; using default loot colors", exc_info=True)
        return FILTER_COLORS_DEFAULT


def is_ignored_item(item_descr) -> bool:
    if is_consumable(item_descr.item_type) or is_non_sigil_mapping(item_descr.item_type):
        return True
    if item_descr.item_type == ItemType.EscalationSigil and get_settings().general.ignore_escalation_sigils:
        return True
    if is_socketable(item_descr.item_type) or item_descr.item_type in {
        ItemType.Material,
        ItemType.Cache,
        ItemType.Cosmetic,
        ItemType.LairBossKey,
    }:
        return True
    return item_descr.seasonal_attribute == SeasonalAttribute.sanctified


def reset_canvas(root, canvas) -> None:
    canvas.delete("all")
    canvas.config(height=0, width=0)
    root.geometry("0x0+0+0")
    root.update_idletasks()
    root.update()


def mark_as_junk() -> None:
    automation.send_hotkey("space")
    time.sleep(0.13)


def mark_as_favorite() -> None:
    LOGGER.info("Mark as favorite")
    automation.send_hotkey("space")
    time.sleep(0.17)
    automation.send_hotkey("space")
    time.sleep(0.13)


def reset_item_status(occupied, inv) -> None:
    for item_slot in occupied:
        if item_slot.is_fav:
            inv.hover_item_with_delay(item_slot)
            automation.send_hotkey("space")
        if item_slot.is_junk:
            inv.hover_item_with_delay(item_slot)
            automation.send_hotkey("space")
            time.sleep(0.15)
            automation.send_hotkey("space")
        time.sleep(0.15)
    if occupied:
        automation.move_pointer(*abs_window_to_monitor((0, 0)))


def drop_item_from_inventory() -> None:
    automation.press_key("ctrl")
    time.sleep(0.03)
    automation.click_pointer("left")
    time.sleep(0.03)
    automation.release_key("ctrl")
    time.sleep(0.10)
