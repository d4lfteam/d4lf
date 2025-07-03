import logging
import queue
import tkinter as tk
from tkinter import font
from tkinter.font import Font

import src.item.descr.read_descr_tts
import src.logger
import src.tts
from config.helper import singleton
from config.loader import IniConfigLoader
from src.cam import Cam
from src.item.data.rarity import ItemRarity
from src.item.filter import Filter, MatchedFilter
from src.scripts.common import ASPECT_UPGRADES_LABEL, COLOR_GREEN, COLOR_ORANGE, is_ignored_item
from src.tts import Publisher
from src.utils.custom_mouse import mouse
from src.utils.window import screenshot

LOGGER = logging.getLogger(__name__)


@singleton
class VisionModeFast:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "white")
        self.root.attributes("-alpha", 1.0)
        self.canvas = tk.Canvas(self.root, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.config(height=self.root.winfo_screenheight(), width=self.root.winfo_screenwidth())
        self.textbox = tk.Text(self.root, bg="black", fg="black", wrap=tk.WORD, borderwidth=0, highlightthickness=0)
        self.textbox.config(state=tk.DISABLED)
        self.clear_timer_id = None
        self.queue = queue.Queue()
        self.draw_from_queue()
        self.is_running = False

    def adjust_textbox_size(self):
        self.textbox.config(state=tk.NORMAL)
        self.textbox.update_idletasks()
        text_content = self.textbox.get(1.0, tk.END)
        line_count = text_content.count("\n")

        text_font = font.Font(font=self.textbox.tag_cget("colored", "font"))
        line_height = text_font.metrics("linespace")
        max_line_length = max(len(line) for line in text_content.splitlines())

        width = max_line_length * text_font.measure("0")
        height = (line_count + 1) * line_height

        mouse_pos = Cam().monitor_to_window(mouse.get_position())
        self.textbox.config(x=mouse_pos[0], y=mouse_pos[1], width=width // 9, height=(height // line_height) - 2)

        self.textbox.config(state=tk.DISABLED)

    def clear_textbox(self):
        if hasattr(self, "textbox"):
            self.textbox.destroy()

    def create_textbox(self):
        self.clear_textbox()
        minimum_font_size = IniConfigLoader().general.minimum_overlay_font_size
        minimum_font = Font(family="Courier New", size=minimum_font_size)
        self.textbox = tk.Text(self.root, bg="black", wrap=tk.WORD, borderwidth=0, highlightthickness=0, font=minimum_font)
        self.textbox.place(x=IniConfigLoader().general.vision_mode_coordinates[0], y=IniConfigLoader().general.vision_mode_coordinates[1])
        self.textbox.config(state=tk.DISABLED)

    def draw_from_queue(self):
        try:
            task = self.queue.get_nowait()
            if task[0] == "text":
                self.insert_colored_text(task[1], task[2])
            if task[0] == "clear":
                self.clear_textbox()
        except queue.Empty:
            pass

        self.canvas.after(10, self.draw_from_queue)

    def insert_colored_text(self, text, color):
        self.create_textbox()
        self.textbox.config(state=tk.NORMAL)
        self.textbox.insert(tk.END, text + "\n", "colored")
        self.textbox.tag_configure("colored", foreground=color)
        self.adjust_textbox_size()
        self.refresh_clear_timer()
        self.textbox.config(state=tk.DISABLED)

    def refresh_clear_timer(self):
        if self.clear_timer_id is not None:
            self.root.after_cancel(self.clear_timer_id)

        self.clear_timer_id = self.root.after(5000, self.clear_textbox)

    def request_clear(self):
        self.queue.put(("clear",))

    def request_draw(self, text, color):
        self.queue.put(("text", text, color))

    def on_tts(self, _):
        try:
            img = Cam().grab()
            item_descr = None
            try:
                item_descr = src.item.descr.read_descr_tts.read_descr()
                LOGGER.debug(f"Parsed item based on TTS: {item_descr}")
            except Exception:
                screenshot("tts_error", img=img)
                LOGGER.exception(f"Error in TTS read_descr. {src.tts.LAST_ITEM=}")
            if item_descr is None:
                return None

            ignored_item = is_ignored_item(item_descr)
            if ignored_item:
                self.request_clear()
                return None

            if item_descr is None:
                LOGGER.info("Unknown Item")
                return self.request_draw("Unknown item", "#ce7e00")

            res = Filter().should_keep(item_descr)
            match = res.keep

            if match:
                color = COLOR_GREEN
                if not res.matched:
                    if item_descr.rarity == ItemRarity.Unique:
                        text = ["Unique"]
                    elif item_descr.rarity == ItemRarity.Mythic:
                        text = ["Mythic (Always Kept)"]
                else:
                    if any(res_matched.profile.endswith(ASPECT_UPGRADES_LABEL) for res_matched in res.matched):
                        color = COLOR_ORANGE
                    text = create_match_text(reversed(res.matched))
                return self.request_draw("\n".join(text), color)
            self.request_clear()
        except Exception:
            LOGGER.exception("Error in vision mode. Please create a bug report")

    def start(self):
        LOGGER.info("Starting Vision Mode")
        Publisher().subscribe(self.on_tts)
        self.is_running = True

    def stop(self):
        LOGGER.info("Stopping Vision Mode")
        self.request_clear()
        Publisher().unsubscribe(self.on_tts)
        self.is_running = False

    def running(self):
        return self.is_running


def create_match_text(matches: list[MatchedFilter]):
    return [f"{match.profile}\n" + "\n".join(f"  - {ma.name}" for ma in match.matched_affixes) for match in matches]
