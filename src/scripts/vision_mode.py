import logging
import math
import time
import tkinter as tk
from tkinter.font import Font

import numpy as np

import src.item.descr.read_descr_tts
import src.logger
import src.tts
from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import HandleRaresType, UseTTSType
from src.config.ui import ResManager
from src.item.data.item_type import ItemType, is_armor, is_consumable, is_jewelry, is_mapping, is_socketable, is_weapon
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr import read_descr
from src.item.filter import Filter
from src.item.find_descr import find_descr
from src.scripts.common import reset_canvas
from src.ui.char_inventory import CharInventory
from src.ui.chest import Chest
from src.utils.custom_mouse import mouse
from src.utils.image_operations import compare_histograms
from src.utils.window import screenshot

LOGGER = logging.getLogger(__name__)


def draw_rect(canvas: tk.Canvas, bullet_width, obj, off, color):
    offset_loc = np.array(obj.loc) + off
    x1 = int(offset_loc[0] - bullet_width / 2)
    y1 = int(offset_loc[1] - bullet_width / 2)
    x2 = int(offset_loc[0] + bullet_width / 2)
    y2 = int(offset_loc[1] + bullet_width / 2)
    canvas.create_rectangle(x1, y1, x2, y2, fill=color)


def draw_text(canvas, text, color, previous_text_y, offset, canvas_center_x) -> int:
    if text is None or text == "":
        return None

    font_name = "Courier New"
    minimum_font_size = IniConfigLoader().general.minimum_overlay_font_size

    font_size = minimum_font_size
    window_height = ResManager().pos.window_dimensions[1]
    if window_height == 1440:
        font_size = minimum_font_size + 1
    elif window_height == 1600:
        font_size = minimum_font_size + 2
    elif window_height == 2160:
        font_size = minimum_font_size + 3

    font = Font(family=font_name, size=font_size)
    width_per_character = font.measure(text) / len(text)
    height_of_character = font.metrics("linespace")
    max_text_length_per_line = canvas_center_x * 2 // width_per_character
    if max_text_length_per_line < len(text):  # Use a smaller font
        font_size = minimum_font_size
        font = Font(family=font_name, size=font_size)
        width_per_character = font.measure(text) / len(text)
        height_of_character = font.metrics("linespace")
        max_text_length_per_line = canvas_center_x * 2 // width_per_character

    # Create a gray rectangle as the background
    text_width = int(width_per_character * len(text))
    if text_width > canvas_center_x * 2:
        text_width = canvas_center_x * 2
    number_of_lines = math.ceil(len(text) / max_text_length_per_line)
    text_height = int(height_of_character * number_of_lines)

    dark_gray_color = "#111111"
    canvas.create_rectangle(
        canvas_center_x - text_width // 2,  # x1
        previous_text_y - offset - text_height,  # y1
        canvas_center_x + text_width // 2,  # x2
        previous_text_y - offset,  # y2
        fill=dark_gray_color,
        outline="",
    )
    canvas.create_text(
        canvas_center_x, previous_text_y - offset, text=text, anchor=tk.S, font=("Courier New", font_size), fill=color, width=text_width
    )
    return int(previous_text_y - offset - text_height)


def create_signal_rect(canvas, w, thick, color):
    canvas.create_rectangle(0, 0, w, thick * 2, outline="", fill=color)
    steps = int((thick * 20) / 40)
    for i in range(100):
        stipple = ""
        if i > 75:
            stipple = "gray75"
        if i > 80:
            stipple = "gray50"
        if i > 95:
            stipple = "gray25"
        if i > 90:
            stipple = "gray12"
        start_y = steps * i
        end_y = steps * (i + 1)

        canvas.create_rectangle(0, start_y, thick * 2, end_y, fill=color, outline="", stipple=stipple)
        canvas.create_rectangle(w - thick * 2, start_y, w, end_y, fill=color, outline="", stipple=stipple)


def vision_mode():
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", "black")
    root.attributes("-alpha", 1.0)
    root.geometry("0x0+0+0")

    thick = int(Cam().window_roi["height"] * 0.0047)
    canvas = tk.Canvas(root, bg="black", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    LOGGER.info("Starting Vision Filter")
    inv = CharInventory()
    chest = Chest()
    img = Cam().grab()
    max_slot_size = chest.get_max_slot_size()
    occ_inv, empty_inv = inv.get_item_slots(img)
    occ_chest, empty_chest = chest.get_item_slots(img)
    possible_centers = []
    possible_centers += [slot.center for slot in occ_inv]
    possible_centers += [slot.center for slot in empty_inv]
    possible_centers += [slot.center for slot in occ_chest]
    possible_centers += [slot.center for slot in empty_chest]
    # add possible centers of equipped items
    for x in ResManager().pos.possible_centers:
        possible_centers.append(x)
    possible_centers = np.array(possible_centers)

    screen_off_x = Cam().window_roi["left"]
    screen_off_y = Cam().window_roi["top"]

    last_top_left_corner = None
    last_center = None
    # Each item must be detected twice and the image must match, this is to avoid
    # getting in item while the fade-in animation and failing to read it properly
    is_confirmed = False
    while True:
        try:
            img = Cam().grab()
            mouse_pos = Cam().monitor_to_window(mouse.get_position())
            # get closest pos to a item center
            delta = possible_centers - mouse_pos
            distances = np.linalg.norm(delta, axis=1)
            closest_index = np.argmin(distances)
            if distances[closest_index] > (max_slot_size * 1.3):
                # avoid randomly looking for items if we are well outside
                found = False
            else:
                item_center = possible_centers[closest_index]
                found, rarity, cropped_descr, item_roi = find_descr(img, item_center)

            top_left_corner = None if not found else item_roi[:2]
            if found:
                if not is_confirmed:
                    found_check, _, cropped_descr_check, _ = find_descr(Cam().grab(), item_center)
                    if found_check:
                        score = compare_histograms(cropped_descr, cropped_descr_check)
                        if score < 0.99:
                            continue
                        is_confirmed = True

                if (
                    last_top_left_corner is None
                    or last_top_left_corner[0] != top_left_corner[0]
                    or last_top_left_corner[1] != top_left_corner[1]
                    or (last_center is not None and last_center[1] != item_center[1])
                ):
                    reset_canvas(root, canvas)

                    # Make the canvas gray for "found the item"
                    x, y, w, h = item_roi
                    off = int(w * 0.1)
                    x -= off
                    y -= off
                    w += off * 2
                    h += off * 5
                    canvas.config(height=h, width=w)
                    create_signal_rect(canvas, w, thick, "#888888")

                    root.geometry(f"{w}x{h}+{x + screen_off_x}+{y + screen_off_y}")
                    root.update_idletasks()
                    root.update()

                    # Check if the item is a match based on our filters
                    last_top_left_corner = top_left_corner
                    last_center = item_center
                    item_descr = None
                    if IniConfigLoader().general.use_tts == UseTTSType.mixed:
                        try:
                            item_descr = src.item.descr.read_descr_tts.read_descr_mixed(cropped_descr)
                            LOGGER.debug(f"Parsed item based on TTS: {item_descr}")
                        except Exception:
                            screenshot("tts_error", img=cropped_descr)
                            LOGGER.exception(f"Error in TTS read_descr. {src.tts.LAST_ITEM=}")
                    else:
                        item_descr = read_descr(rarity, cropped_descr, False)
                    if item_descr is None:
                        last_center = None
                        last_top_left_corner = None
                        is_confirmed = False
                        continue

                    ignored_item = False
                    if is_consumable(item_descr.item_type):
                        LOGGER.info("Matched: Consumable")
                        ignored_item = True
                    if is_mapping(item_descr.item_type):
                        LOGGER.info("Matched: Mapping")
                        ignored_item = True
                    if is_socketable(item_descr.item_type):
                        LOGGER.info("Matched: Socketable")
                        ignored_item = True
                    elif item_descr.item_type == ItemType.Tribute:
                        LOGGER.info("Matched: Tribute")
                        ignored_item = True
                    elif item_descr.item_type == ItemType.Material:
                        LOGGER.info("Matched: Material")
                        ignored_item = True
                    if (
                        item_descr.rarity == ItemRarity.Rare
                        and (is_armor(item_descr.item_type) or is_weapon(item_descr.item_type) or is_jewelry(item_descr.item_type))
                        and IniConfigLoader().general.handle_rares in [HandleRaresType.ignore, HandleRaresType.junk]
                    ):
                        LOGGER.info("Matched: Rare, ignore Item")
                        ignored_item = True

                    if ignored_item:
                        create_signal_rect(canvas, w, thick, "#00b3b3")
                        root.update_idletasks()
                        root.update()
                        continue

                    if item_descr is None:
                        LOGGER.info("Unknown Item")
                        create_signal_rect(canvas, w, thick, "#ce7e00")
                        root.update_idletasks()
                        root.update()
                        continue

                    res = Filter().should_keep(item_descr)
                    match = res.keep

                    # Adapt colors based on config
                    if match:
                        create_signal_rect(canvas, w, thick, "#23fc5d")

                        # show all info strings of the profiles
                        text_y = h
                        for match in reversed(res.matched):
                            text_y = draw_text(canvas, match.profile, "#23fc5d", text_y, 5, w // 2)
                        # Show matched bullets
                        if item_descr is not None and len(res.matched) > 0:
                            bullet_width = thick * 3
                            for affix in res.matched[0].matched_affixes:
                                if affix.loc is not None:
                                    draw_rect(canvas, bullet_width, affix, off, "#23fc5d")

                            if item_descr.aspect is not None and any(m.did_match_aspect for m in res.matched):
                                draw_rect(canvas, bullet_width, item_descr.aspect, off, "#23fc5d")
                    elif not match:
                        create_signal_rect(canvas, w, thick, "#fc2323")

                    root.update_idletasks()
                    root.update()
            else:
                reset_canvas(root, canvas)
                last_center = None
                last_top_left_corner = None
                is_confirmed = False
                time.sleep(0.15)
        except Exception:
            LOGGER.exception("Error in vision mode. Please create a bug report")
            time.sleep(1)
