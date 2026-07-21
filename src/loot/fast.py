import collections.abc
import logging
import queue
import tkinter as tk
from tkinter import font
from tkinter.font import Font
from typing import Literal

import src.perception
from src.desktop import call_on_ui_thread, create_overlay_toplevel, get_root
from src.item import ASPECT_UPGRADES_LABEL, Filter, ItemRarity, MatchedFilter
from src.loot.colors import get_filter_colors, is_ignored_item
from src.loot.singleton import singleton
from src.perception import Publisher, capture, screenshot
from src.settings import get_settings, get_ui_coordinates

LOGGER = logging.getLogger(__name__)

Iterable = collections.abc.Iterable

type FastVisionTask = tuple[Literal["clear"]] | tuple[Literal["text"], str, str]


@singleton
class VisionModeFast:
    def __init__(self):
        self.root: tk.Toplevel
        self.canvas: tk.Canvas
        self.textbox: tk.Text | None = None
        self.clear_timer_id: str | None = None
        self.queue: queue.Queue[FastVisionTask] = queue.Queue()
        self.is_running: bool = False

        def _build_ui() -> None:
            self.root, self.canvas = create_overlay_toplevel(get_root())
            self.canvas.config(height=self.root.winfo_screenheight(), width=self.root.winfo_screenwidth())
            self.textbox = tk.Text(self.root, bg="black", fg="black", wrap=tk.WORD, borderwidth=0, highlightthickness=0)
            self.textbox.config(state=tk.DISABLED)
            self.draw_from_queue()

        # Widget creation and every subsequent Tk call must happen on the
        # shared UI thread, not whichever thread constructs this singleton.
        call_on_ui_thread(_build_ui)

    def adjust_textbox_size(self):
        textbox = self.textbox
        if textbox is None:
            return
        textbox.config(state=tk.NORMAL)
        textbox.update_idletasks()
        text_content = textbox.get(1.0, tk.END)
        line_count = text_content.count("\n")

        text_font = font.Font(font=textbox.cget("font"))
        line_height = text_font.metrics("linespace")
        lines = text_content.splitlines()

        width = max(text_font.measure(line) for line in lines) + 4
        height = max(1, line_count) * line_height

        textbox.place_configure(width=width, height=height)

        textbox.config(state=tk.DISABLED)

    def clear_textbox(self):
        textbox = self.textbox
        if textbox is not None:
            textbox.destroy()
            self.textbox = None

    def create_textbox(self):
        self.clear_textbox()
        minimum_font_size = get_settings().general.minimum_overlay_font_size
        minimum_font = Font(family="Courier New", size=minimum_font_size)
        self.textbox = tk.Text(
            self.root, bg="black", wrap=tk.WORD, borderwidth=0, highlightthickness=0, font=minimum_font
        )
        if get_settings().advanced_options.fast_vision_mode_coordinates is None:
            x = get_ui_coordinates().resolution[0] / 2
            y = get_ui_coordinates().resolution[1] * 2 / 3
        else:
            coordinates = get_settings().advanced_options.fast_vision_mode_coordinates
            if coordinates is None:
                return
            x, y = coordinates
        self.textbox.place(x=x, y=y)
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

    def insert_colored_text(self, text: str, color: str) -> None:
        self.create_textbox()
        textbox = self.textbox
        if textbox is None:
            return
        textbox.config(state=tk.NORMAL)
        textbox.insert(tk.END, text + "\n", "colored")
        textbox.tag_configure("colored", foreground=color)
        self.adjust_textbox_size()
        self.refresh_clear_timer()
        textbox.config(state=tk.DISABLED)

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
            item_descr = None
            try:
                item_descr = src.perception.read_latest_item()
                LOGGER.debug(f"Parsed item based on TTS: {item_descr}")
            except Exception:
                img = capture()
                screenshot("tts_error", img=img)
                LOGGER.exception(f"Error in TTS read_descr. {src.perception.latest_item_lines()=}")
            if item_descr is None:
                return None

            ignored_item = is_ignored_item(item_descr)
            if ignored_item:
                self.request_clear()
                return None

            if item_descr is None:
                LOGGER.info("Unknown Item")
                return self.request_draw("Unknown item", "#ce7e00")

            feedback = fast_feedback(item_descr, Filter().should_keep(item_descr))
            if feedback is None:
                self.request_clear()
                return None
            text, color = feedback
            return self.request_draw(text, color)
        except Exception:
            LOGGER.exception("Error in vision mode. Please create a bug report")

    def start(self):
        LOGGER.info("Starting Vision Mode")
        Publisher().subscribe_item(self.on_tts)
        self.is_running = True

    def stop(self):
        LOGGER.info("Stopping Vision Mode")
        self.request_clear()
        Publisher().unsubscribe_item(self.on_tts)
        self.is_running = False

    def running(self):
        return self.is_running


def create_match_text(matches: Iterable[MatchedFilter]) -> list[str]:
    result: list[str] = []
    for match in matches:
        match_list = [f"  - {ma.name}" for ma in match.matched_affixes]
        if match.aspect_match:
            match_list.append("  - Aspect")
        if match.set_match:
            match_list.append("  - Set")
        result.append(f"{match.profile}\n" + "\n".join(match_list))

    return result


def fast_feedback(item_descr, filter_result) -> tuple[str, str] | None:
    """Return the immediate tooltip feedback for a parsed item and its result."""
    colors = get_filter_colors()
    if not filter_result.keep:
        return None

    if not filter_result.matched:
        if item_descr.rarity == ItemRarity.Unique:
            text = ["Unique"]
        elif item_descr.rarity == ItemRarity.Mythic:
            text = ["Mythic (Always Kept)"]
        else:
            text = []
        return "\n".join(text), colors.matched

    color = (
        colors.codex_upgrade
        if any(match.profile.endswith(ASPECT_UPGRADES_LABEL) for match in filter_result.matched)
        else colors.matched
    )
    return "\n".join(create_match_text(reversed(filter_result.matched))), color
