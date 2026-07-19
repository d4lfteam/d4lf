"""Tk rendering for the highlighting vision mode."""

import math
import queue
import tkinter as tk
from tkinter.font import Font
from typing import TYPE_CHECKING, Any

import numpy as np

from src.item import ASPECT_UPGRADES_LABEL
from src.loot.colors import get_filter_colors, reset_canvas
from src.settings import get_settings, get_ui_coordinates

DARK_GRAY_BG = "#111111"

if TYPE_CHECKING:
    from src.item import FilterResult
    from src.perception import LocatorResult


class HighlightingRenderer:
    def draw_rect(self: Any, canvas: tk.Canvas, bullet_width: int, loc: tuple[int, int], off: int, color: str) -> None:
        offset_loc = np.array(loc) + off
        x1 = int(offset_loc[0] - bullet_width / 2)
        y1 = int(offset_loc[1] - bullet_width / 2)
        x2 = int(offset_loc[0] + bullet_width / 2)
        y2 = int(offset_loc[1] + bullet_width / 2)
        canvas.create_rectangle(x1, y1, x2, y2, fill=color)

    def draw_text(
        self: Any, canvas: tk.Canvas, text: str, color: str, previous_text_y: int, offset: int, canvas_center_x: int
    ) -> int:
        if not text:
            return previous_text_y

        font_name = "Courier New"
        minimum_font_size = get_settings().general.minimum_overlay_font_size

        font_size = minimum_font_size
        window_height = get_ui_coordinates().pos.window_dimensions[1]
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
        text_width = min(text_width, canvas_center_x * 2)
        number_of_lines = math.ceil(len(text) / max_text_length_per_line)
        text_height = int(height_of_character * number_of_lines)

        canvas.create_rectangle(
            canvas_center_x - text_width // 2,  # x1
            previous_text_y - offset - text_height,  # y1
            canvas_center_x + text_width // 2,  # x2
            previous_text_y - offset,  # y2
            fill=DARK_GRAY_BG,
            outline="",
        )
        canvas.create_text(
            canvas_center_x,
            previous_text_y - offset,
            text=text,
            anchor=tk.S,
            font=("Courier New", font_size),
            fill=color,
            width=text_width,
        )
        return int(previous_text_y - offset - text_height)

    def create_signal_rect(self: Any, canvas, w, thick, color):
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

    def draw_from_queue(self: Any):
        try:
            task = self.queue.get_nowait()
            # LOGGER.debug(f"Queue size: {self.queue.qsize()}, task: {task}")
            if task[0] == "clear":
                reset_canvas(self.root, self.canvas)
                self.is_cleared = True
            else:
                item_desc = task[1]
                if item_desc == self.current_item:
                    self.is_cleared = False
                    if task[0] == "empty":
                        self.draw_empty_outline(task[2], task[3], task[4])
                    if task[0] == "match":
                        self.draw_match_outline(task[2], task[3], task[4])
                    if task[0] == "codex_upgrade":
                        self.draw_codex_upgrade_outline(task[2], task[3])
                    if task[0] == "no_match":
                        self.draw_no_match_outline(task[2])
        except queue.Empty:
            pass

        self.canvas.after(10, self.draw_from_queue)

    def draw_empty_outline(self: Any, item_roi, color, text: str | None):
        reset_canvas(self.root, self.canvas)

        x, y, w, h, off = self.get_coords_from_roi(item_roi)
        self.canvas.config(height=h, width=w)
        self.create_signal_rect(self.canvas, w, self.thick, color)

        if text:
            self.draw_text(self.canvas, text, color, h, 5, w // 2)

        self.root.geometry(f"{w}x{h}+{x + self.screen_off_x}+{y + self.screen_off_y}")
        self.root.update_idletasks()
        self.root.update()

    def draw_match_outline(self: Any, item_roi, should_keep_res, locator_result: LocatorResult | None):
        reset_canvas(self.root, self.canvas)

        x, y, w, h, off = self.get_coords_from_roi(item_roi)
        self.canvas.config(height=h, width=w)
        self.create_signal_rect(self.canvas, w, self.thick, get_filter_colors().matched)

        # show all info strings of the profiles
        text_y = h
        for match in reversed(should_keep_res.matched):
            text = match.profile
            if match.set_match:
                text = text + " (incl. Set)"
            text_y = self.draw_text(self.canvas, text, get_filter_colors().matched, text_y, 5, w // 2)
        # Show matched bullets
        if locator_result and locator_result.reliable and len(should_keep_res.matched) > 0:
            bullet_width = self.thick * 3
            for marker in locator_result.markers:
                self.draw_rect(self.canvas, bullet_width, marker.center, off, get_filter_colors().matched)

        self.root.geometry(f"{w}x{h}+{x + self.screen_off_x}+{y + self.screen_off_y}")
        self.root.update_idletasks()
        self.root.update()

    def draw_no_match_outline(self: Any, item_roi):
        reset_canvas(self.root, self.canvas)

        x, y, w, h, off = self.get_coords_from_roi(item_roi)
        self.canvas.config(height=h, width=w)
        self.create_signal_rect(self.canvas, w, self.thick, get_filter_colors().no_match)
        self.root.geometry(f"{w}x{h}+{x + self.screen_off_x}+{y + self.screen_off_y}")
        self.root.update_idletasks()
        self.root.update()

    def draw_codex_upgrade_outline(self: Any, item_roi, should_keep_result: FilterResult):
        reset_canvas(self.root, self.canvas)

        x, y, w, h, off = self.get_coords_from_roi(item_roi)
        self.canvas.config(height=h, width=w)

        self.create_signal_rect(self.canvas, w, self.thick, get_filter_colors().codex_upgrade)

        # show string indicating that this item upgrades the codex
        if len(should_keep_result.matched) == 1 and should_keep_result.matched[0].profile == ASPECT_UPGRADES_LABEL:
            self.draw_text(self.canvas, "Codex Upgrade", get_filter_colors().codex_upgrade, h, 5, w // 2)
        else:
            # This matched an Aspects section in a profile, write the profiles
            text_y = h
            for match in reversed(should_keep_result.matched):
                text_y = self.draw_text(
                    self.canvas, match.profile, get_filter_colors().codex_upgrade, text_y, 5, w // 2
                )

        self.root.geometry(f"{w}x{h}+{x + self.screen_off_x}+{y + self.screen_off_y}")
        self.root.update_idletasks()
        self.root.update()

    def get_coords_from_roi(self: Any, item_roi):
        x, y, w, h = item_roi
        off = int(w * 0.1)
        x -= off
        y -= off
        w += off * 2
        h += off * 5
        return x, y, w, h, off
