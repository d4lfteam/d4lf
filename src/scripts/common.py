from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tkinter import Canvas

if sys.platform != "darwin":
    import keyboard

from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.item.data.item_type import ItemType, is_consumable, is_non_sigil_mapping, is_socketable
from src.item.data.rarity import ItemRarity
from src.utils.custom_mouse import mouse

try:
    from src.config.ui import ResManager
except Exception:  # pragma: no cover
    ResManager = None  # type: ignore[assignment]


if TYPE_CHECKING:
    from src.item.models import Item

LOGGER = logging.getLogger(__name__)

SETUP_INSTRUCTIONS_URL = "https://github.com/d4lfteam/d4lf/blob/main/README.md#how-to-setup"


@dataclass(frozen=True, slots=True)
class FilterColors:
    """Color palette used by the loot filter / vision overlays."""

    matched: str
    no_match: str
    codex_upgrade: str
    processing: str
    unhandled: str


# Default palette.
FILTER_COLORS_DEFAULT = FilterColors(
    matched="#23fc5d",  # COLOR_GREEN-Matched a profile
    no_match="#fc2323",  # COLOR_RED-Matched no profiles at all
    codex_upgrade="#fca503",  # COLOR_ORANGE-Matched a codex upgrade
    processing="#888888",  # COLOR_GREY-Still processing or can't find the info we expect
    unhandled="#00b3b3",  # COLOR_BLUE-We recognize this as an item, but it is not one we handle
)

# Colorblind-friendly palette (Okabe-Ito inspired).
FILTER_COLORS_COLORBLIND = FilterColors(
    matched="#56B4E9",  # COLOR_BLUE-Matched a profile
    no_match="#D55E00",  # COLOR_VERMILLION-Matched no profiles at all
    codex_upgrade="#E69F00",  # COLOR_ORANGE-Matched a codex upgrade
    processing="#888888",  # COLOR_GREY-Still processing or can't find the info we expect
    unhandled="#CC79A7",  # COLOR_PURPLE-We recognize this as an item, but it is not one we handle
)


def get_filter_colors() -> FilterColors:
    """Return the active palette (default vs. colorblind mode)."""
    try:
        if IniConfigLoader().general.colorblind_mode:
            return FILTER_COLORS_COLORBLIND
    except Exception:
        # Fail-safe: if config isn't available yet, use defaults.
        LOGGER.debug("get_filter_colors(): config unavailable; using default palette", exc_info=True)
    return FILTER_COLORS_DEFAULT


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


# --- Shared overlay text helper (used by paragon_overlay & vision modes) ---
def _scaled_overlay_font_size(minimum_font_size: int, window_height: int | None) -> int:
    """Legacy scaling behavior from vision_mode_with_highlighting."""
    if window_height == 1440:
        return minimum_font_size + 1
    if window_height == 1600:
        return minimum_font_size + 2
    if window_height == 2160:
        return minimum_font_size + 3
    return minimum_font_size


def draw_text_with_background(
    canvas: Canvas,
    text: str,
    color: str,
    previous_text_y: int,
    offset: int,
    canvas_center_x: int,
    *,
    background_color: str = "#111111",
    font_name: str = "Courier New",
    window_height: int | None = None,
) -> int | None:
    """Draw wrapped text centered at canvas_center_x with a background box.

    Thread-safe relative to overlays that run outside the main thread because this
    implementation avoids creating tkinter.font.Font() objects (which can trigger
    'main thread is not in main loop' in some environments). Instead, it measures
    the rendered text using a temporary canvas text item and canvas.bbox().
    """
    if not text:
        return None

    minimum_font_size = IniConfigLoader().general.minimum_overlay_font_size

    # If caller didn't provide window_height, attempt to fetch it lazily.
    if window_height is None:
        try:
            if ResManager is not None:
                window_height = ResManager().pos.window_dimensions[1]
        except Exception:
            window_height = None

    max_width = int(canvas_center_x * 2)
    font_size = _scaled_overlay_font_size(minimum_font_size, window_height)

    def _measure_bbox(size: int):
        tmp_id = canvas.create_text(
            -10000, -10000, text=text, anchor="nw", font=(font_name, size), fill=color, width=max_width
        )
        bbox = canvas.bbox(tmp_id)  # (x1, y1, x2, y2) or None
        canvas.delete(tmp_id)
        return bbox

    bbox = _measure_bbox(font_size)
    if not bbox:
        return None

    text_w = int(bbox[2] - bbox[0])
    text_h = int(bbox[3] - bbox[1])

    # Legacy-ish fallback: if it basically fills the whole width and we used the
    # scaled font, try the minimum font size.
    if font_size != minimum_font_size and text_w >= max_width - 2:
        bbox2 = _measure_bbox(minimum_font_size)
        if bbox2:
            font_size = minimum_font_size
            text_w = int(bbox2[2] - bbox2[0])
            text_h = int(bbox2[3] - bbox2[1])

    left = int(canvas_center_x - text_w // 2)
    right = int(canvas_center_x + text_w // 2)
    bottom = int(previous_text_y - offset)
    top = int(bottom - text_h)

    rect_id = canvas.create_rectangle(left, top, right, bottom, fill=background_color, outline="")
    text_id = canvas.create_text(
        canvas_center_x, bottom, text=text, anchor="s", font=(font_name, font_size), fill=color, width=max_width
    )
    # Ensure text is above background.
    canvas.tag_raise(text_id, rect_id)

    return top
