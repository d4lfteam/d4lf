import logging
import math
import queue
import threading
import time
import tkinter as tk
from tkinter.font import Font

import numpy as np

import src.item.descr.read_descr_tts
import src.logger
import src.tts
from config.helper import singleton
from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.ui import ResManager
from src.item.data.item_type import ItemType
from src.item.data.rarity import is_junk_rarity
from src.item.filter import Filter
from src.item.find_descr import find_descr
from src.item.models import Item
from src.scripts.common import is_ignored_item, reset_canvas
from src.tts import Publisher
from src.ui.char_inventory import CharInventory
from src.ui.stash import Stash
from src.ui.vendor import Vendor
from src.utils.custom_mouse import mouse
from src.utils.image_operations import compare_histograms
from src.utils.process_handler import kill_thread
from src.utils.window import screenshot

LOGGER = logging.getLogger(__name__)


@singleton
class VisionModeWithHighlighting:
    def __init__(self):
        super().__init__()
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 1.0)
        self.root.attributes("-transparentcolor", "white")
        self.canvas = tk.Canvas(self.root, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.clear_when_item_not_selected_thread = None
        self.evaluate_item_thread = None
        self.current_item = None
        self.is_cleared = True
        self.queue = queue.Queue()
        self.draw_from_queue()
        self.is_running = False
        self.root.geometry("0x0+0+0")
        self.thick = int(Cam().window_roi["height"] * 0.0047)

        inv = CharInventory()
        stash = Stash()
        vendor = Vendor()
        img = Cam().grab()
        self.max_slot_size = stash.get_max_slot_size()
        occ_inv, empty_inv = inv.get_item_slots(img)
        occ_stash, empty_stash = stash.get_item_slots(img)
        occ_vendor, empty_vendor = vendor.get_item_slots(img)
        possible_centers = []
        possible_centers += [slot.center for slot in occ_inv]
        possible_centers += [slot.center for slot in empty_inv]

        # add possible centers of equipped items
        for x in ResManager().pos.possible_centers:
            possible_centers.append(x)

        possible_vendor_centers = possible_centers.copy()
        possible_vendor_centers += [slot.center for slot in occ_vendor]
        possible_vendor_centers += [slot.center for slot in empty_vendor]

        possible_centers += [slot.center for slot in occ_stash]
        possible_centers += [slot.center for slot in empty_stash]

        self.possible_centers = np.array(possible_centers)
        self.possible_vendor_centers = np.array(possible_vendor_centers)

        self.screen_off_x = Cam().window_roi["left"]
        self.screen_off_y = Cam().window_roi["top"]

    def draw_rect(self, canvas: tk.Canvas, bullet_width, obj, off, color):
        offset_loc = np.array(obj.loc) + off
        x1 = int(offset_loc[0] - bullet_width / 2)
        y1 = int(offset_loc[1] - bullet_width / 2)
        x2 = int(offset_loc[0] + bullet_width / 2)
        y2 = int(offset_loc[1] + bullet_width / 2)
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color)

    def draw_text(self, canvas, text, color, previous_text_y, offset, canvas_center_x) -> int:
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

    def create_signal_rect(self, canvas, w, thick, color):
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

    def draw_from_queue(self):
        try:
            task = self.queue.get_nowait()
            if task[0] == "clear":
                reset_canvas(self.root, self.canvas)
                self.is_cleared = True
            else:
                item_desc = task[1]
                if item_desc == self.current_item:
                    self.is_cleared = False
                    if task[0] == "empty":
                        self.draw_empty_outline(task[2], task[3])
                    if task[0] == "match":
                        self.draw_match_outline(task[2], task[3], task[4])
                    if task[0] == "codex_upgrade":
                        self.draw_codex_upgrade_outline(task[2], task[1])
                    if task[0] == "no_match":
                        self.draw_no_match_outline(task[2])
        except queue.Empty:
            pass

        self.canvas.after(10, self.draw_from_queue)

    def draw_empty_outline(self, item_roi, color):
        reset_canvas(self.root, self.canvas)

        # Make the canvas gray for "found the item"
        x, y, w, h, off = self.get_coords_from_roi(item_roi)
        self.canvas.config(height=h, width=w)
        self.create_signal_rect(self.canvas, w, self.thick, color)

        self.root.geometry(f"{w}x{h}+{x + self.screen_off_x}+{y + self.screen_off_y}")
        self.root.update_idletasks()
        self.root.update()

    def draw_match_outline(self, item_roi, should_keep_res, item_descr):
        x, y, w, h, off = self.get_coords_from_roi(item_roi)
        self.create_signal_rect(self.canvas, w, self.thick, "#23fc5d")

        # show all info strings of the profiles
        text_y = h
        for match in reversed(should_keep_res.matched):
            text_y = self.draw_text(self.canvas, match.profile, "#23fc5d", text_y, 5, w // 2)
        # Show matched bullets
        if item_descr is not None and len(should_keep_res.matched) > 0:
            bullet_width = self.thick * 3
            for affix in should_keep_res.matched[0].matched_affixes:
                if affix.loc is not None:
                    self.draw_rect(self.canvas, bullet_width, affix, off, "#23fc5d")

            if item_descr.aspect is not None and any(m.did_match_aspect for m in should_keep_res.matched):
                self.draw_rect(self.canvas, bullet_width, item_descr.aspect, off, "#23fc5d")

        self.root.update_idletasks()
        self.root.update()

    def draw_no_match_outline(self, item_roi):
        x, y, w, h, off = self.get_coords_from_roi(item_roi)
        self.create_signal_rect(self.canvas, w, self.thick, "#fc2323")
        self.root.update_idletasks()
        self.root.update()

    def draw_codex_upgrade_outline(self, item_roi, item_descr):
        x, y, w, h, off = self.get_coords_from_roi(item_roi)

        self.create_signal_rect(self.canvas, w, self.thick, "#fca503")

        # show string indicating that this item upgrades the codex
        self.draw_text(self.canvas, "Codex Upgrade", "#fca503", h, 5, w // 2)

        self.root.update_idletasks()
        self.root.update()

    def on_tts(self, _):
        img = Cam().grab()
        item_descr = None
        try:
            item_descr = src.item.descr.read_descr_tts.read_descr()
            LOGGER.debug(f"Parsed item based on TTS: {item_descr}")
        except Exception:
            screenshot("tts_error", img=img)
            LOGGER.exception(f"Error in TTS read_descr. {src.tts.LAST_ITEM=}")
        if item_descr is None:
            self.request_clear()
            return

        self.current_item = item_descr

        # Kick off a thread that will evaluate the item and queue up the appropriate drawings.
        # If one already exists we'll kill it since a new item has come in
        if self.evaluate_item_thread:
            kill_thread(self.evaluate_item_thread)

        self.evaluate_item_thread = threading.Thread(target=self.evaluate_item_and_queue_draw, args=(item_descr,), daemon=True)
        self.evaluate_item_thread.start()

    def evaluate_item_and_queue_draw(self, item_descr: Item):
        self.request_clear()
        if self.clear_when_item_not_selected_thread:
            kill_thread(self.clear_when_item_not_selected_thread)
            self.clear_when_item_not_selected_thread = None

        last_top_left_corner = None
        last_center = None
        # Each item must be detected twice and the image must match, this is to avoid
        # getting in item while the fade-in animation and failing to read it properly
        is_confirmed = False
        retry_count = 0
        try:
            while retry_count < 5 and not is_confirmed:
                retry_count += 1
                mouse_pos = Cam().monitor_to_window(mouse.get_position())
                # get closest pos to a item center
                centers_to_use = self.possible_vendor_centers if item_descr.is_in_shop else self.possible_centers
                delta = centers_to_use - mouse_pos
                distances = np.linalg.norm(delta, axis=1)
                closest_index = np.argmin(distances)
                item_center = centers_to_use[closest_index]

                # Before we get the cropped_descr we need to ensure there is no previous overlay on screen
                while not self.is_cleared:
                    time.sleep(0.10)
                found, rarity, cropped_descr, item_roi = find_descr(Cam().grab(), item_center)

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
                        ignored_item = is_ignored_item(item_descr)
                        # Make the canvas gray for "found the item" or blue for "ignored this item"
                        if ignored_item:
                            self.request_empty_outline(item_descr, item_roi, "#00b3b3")
                        else:
                            self.request_empty_outline(item_descr, item_roi, "#888888")

                        # Since we've now drawn something we kick off a thread to remove the drawing
                        # if the item is unselected. It is also automatically removed if a different
                        # TTS item comes in.
                        if not self.clear_when_item_not_selected_thread:
                            self.clear_when_item_not_selected_thread = threading.Thread(
                                target=self.check_for_item_still_selected, args=(item_center,), daemon=True
                            )
                            self.clear_when_item_not_selected_thread.start()

                        if ignored_item:
                            return

                        # Check if the item is a match based on our filters
                        last_top_left_corner = top_left_corner
                        last_center = item_center

                        if item_descr == self.current_item:
                            # We need to get the item_descr again but this time with affix locations
                            if item_descr.item_type == ItemType.Sigil or is_junk_rarity(item_descr.rarity):
                                # We won't highlight specific affixes for sigils. We'll see if people complain
                                # We're also marking all common/magic/rares as junk so no need to do the image lookup
                                item_descr_with_loc = item_descr
                            else:
                                item_descr_with_loc = src.item.descr.read_descr_tts.read_descr_mixed(cropped_descr)
                            res = Filter().should_keep(item_descr_with_loc)
                            match = res.keep

                            # Adapt colors based on config
                            if match:
                                if len(res.matched) == 1 and res.matched[0].profile == "Aspects":
                                    self.request_codex_upgrade_box(item_descr, item_roi)
                                else:
                                    self.request_match_box(item_descr, item_roi, res, item_descr_with_loc)
                            elif not match:
                                self.request_no_match_box(item_descr, item_roi)
                else:
                    self.request_clear()
                    last_center = None
                    last_top_left_corner = None
                    is_confirmed = False
                    time.sleep(0.15)
        except Exception:
            LOGGER.exception("Error in vision mode. Please create a bug report")
        finally:
            self.evaluate_item_thread = None

    def check_for_item_still_selected(self, item_center):
        while True:
            found_check, _, _, _ = find_descr(Cam().grab(), item_center)
            if not found_check:
                self.request_clear()
                self.clear_when_item_not_selected_thread = None
                break
            time.sleep(0.15)

    def get_coords_from_roi(self, item_roi):
        x, y, w, h = item_roi
        off = int(w * 0.1)
        x -= off
        y -= off
        w += off * 2
        h += off * 5
        return x, y, w, h, off

    def request_clear(self):
        self.queue.put(("clear",))

    def request_empty_outline(self, item_descr, item_roi, color):
        self.queue.put(("empty", item_descr, item_roi, color))

    def request_match_box(self, item_descr, item_roi, should_keep_res, item_descr_with_affix):
        self.queue.put(("match", item_descr, item_roi, should_keep_res, item_descr_with_affix))

    def request_no_match_box(self, item_descr, item_roi):
        self.queue.put(("no_match", item_descr, item_roi))

    def request_codex_upgrade_box(self, item_descr, item_roi):
        self.queue.put(("codex_upgrade", item_descr, item_roi))

    def start(self):
        LOGGER.info("Starting Vision Mode")
        Publisher().subscribe(self.on_tts)
        self.is_running = True

    def stop(self):
        LOGGER.info("Stopping Vision Mode")
        self.request_clear()
        if self.evaluate_item_thread:
            kill_thread(self.evaluate_item_thread)
            self.evaluate_item_thread = None
        if self.clear_when_item_not_selected_thread:
            kill_thread(self.clear_when_item_not_selected_thread)
            self.clear_when_item_not_selected_thread = None
        Publisher().unsubscribe(self.on_tts)
        self.is_running = False

    def running(self):
        return self.is_running
