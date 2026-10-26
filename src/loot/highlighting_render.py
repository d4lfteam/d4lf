"""Tk rendering for the highlighting vision mode."""

import logging
import queue
import tkinter as tk
from tkinter.font import Font
from typing import TYPE_CHECKING

import numpy as np

from src.item import ASPECT_UPGRADES_LABEL
from src.loot.colors import get_filter_colors, reset_canvas, visible_missing_affixes
from src.settings import get_settings, get_ui_coordinates

LOGGER = logging.getLogger(__name__)

DARK_GRAY_BG = "#111111"
WINDOW_HEIGHT_1440 = 1440
WINDOW_HEIGHT_1600 = 1600
WINDOW_HEIGHT_2160 = 2160

SIGNAL_GRAY75_AFTER = 75
SIGNAL_GRAY50_AFTER = 80
SIGNAL_GRAY25_AFTER = 95
SIGNAL_GRAY12_AFTER = 90

if TYPE_CHECKING:
    from src.item import FilterResult
    from src.loot.highlighting import _VisionModeWithHighlighting
    from src.perception import LocatorResult


class HighlightingRenderer:
    def draw_rect(
        self: _VisionModeWithHighlighting,
        canvas: tk.Canvas,
        bullet_width: int,
        loc: tuple[int, int],
        off: int,
        color: str,
    ) -> None:
        offset_loc = np.array(loc) + off
        x1 = int(offset_loc[0] - bullet_width / 2)
        y1 = int(offset_loc[1] - bullet_width / 2)
        x2 = int(offset_loc[0] + bullet_width / 2)
        y2 = int(offset_loc[1] + bullet_width / 2)
        canvas.create_rectangle(x1, y1, x2, y2, fill=color)

    def draw_text(
        self: _VisionModeWithHighlighting,
        canvas: tk.Canvas,
        text: str,
        color: str,
        previous_text_y: int,
        offset: int,
        canvas_center_x: int,
    ) -> int:
        if not text:
            return previous_text_y

        font_name = "Courier New"
        minimum_font_size = get_settings().general.minimum_overlay_font_size

        font_size = minimum_font_size
        window_height = get_ui_coordinates().pos.window_dimensions[1]
        if window_height == WINDOW_HEIGHT_1440:
            font_size = minimum_font_size + 1
        elif window_height == WINDOW_HEIGHT_1600:
            font_size = minimum_font_size + 2
        elif window_height == WINDOW_HEIGHT_2160:
            font_size = minimum_font_size + 3

        width_per_character = Font(family=font_name, size=font_size).measure(text) / len(text)
        if canvas_center_x * 2 // width_per_character < len(text):  # Use a smaller font
            font_size = minimum_font_size
            width_per_character = Font(family=font_name, size=font_size).measure(text) / len(text)

        text_width = min(int(width_per_character * len(text)), canvas_center_x * 2)
        text_id = canvas.create_text(
            canvas_center_x,
            previous_text_y - offset,
            text=text,
            anchor=tk.S,
            font=(font_name, font_size),
            fill=color,
            width=text_width,
        )
        # Tk wraps at word boundaries, so use the rendered bounds instead of estimating the line count
        x1, y1, x2, y2 = canvas.bbox(text_id)
        background_id = canvas.create_rectangle(x1, y1, x2, y2, fill=DARK_GRAY_BG, outline="")
        canvas.tag_lower(background_id, text_id)
        return y1

    def create_signal_rect(
        self: _VisionModeWithHighlighting, canvas: tk.Canvas, w: int, thick: int, color: str
    ) -> None:
        canvas.create_rectangle(0, 0, w, thick * 2, outline="", fill=color)
        steps = int((thick * 20) / 40)
        for i in range(100):
            stipple = ""
            if i > SIGNAL_GRAY75_AFTER:
                stipple = "gray75"
            if i > SIGNAL_GRAY50_AFTER:
                stipple = "gray50"
            if i > SIGNAL_GRAY25_AFTER:
                stipple = "gray25"
            if i > SIGNAL_GRAY12_AFTER:
                stipple = "gray12"
            start_y = steps * i
            end_y = steps * (i + 1)

            canvas.create_rectangle(0, start_y, thick * 2, end_y, fill=color, outline="", stipple=stipple)
            canvas.create_rectangle(w - thick * 2, start_y, w, end_y, fill=color, outline="", stipple=stipple)

    def draw_from_queue(self: _VisionModeWithHighlighting) -> None:
        try:
            task = self.queue.get_nowait()
            # LOGGER.debug(f"Queue size: {self.queue.qsize()}, task: {task}")
            if task[0] == "clear":
                reset_canvas(self.root, self.canvas)
                task[1].set()
            else:
                item_desc = task[1]
                if item_desc == self.current_item:
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
        except Exception:
            LOGGER.exception("Error while drawing highlighting overlay")
        finally:
            # Always reschedule, otherwise a single drawing error would stop the redraw loop for good.
            self.canvas.after(10, self.draw_from_queue)

    def draw_empty_outline(
        self: _VisionModeWithHighlighting, item_roi: tuple[int, int, int, int], color: str, text: str | None
    ) -> None:
        reset_canvas(self.root, self.canvas)

        x, y, w, h, _off = self.get_coords_from_roi(item_roi)
        self.canvas.config(height=h, width=w)
        self.create_signal_rect(self.canvas, w, self.thick, color)

        if text is not None and text != "":
            self.draw_text(self.canvas, text, color, h, 5, w // 2)

        self.root.geometry(f"{w}x{h}+{x + self.screen_off_x}+{y + self.screen_off_y}")
        self.root.update_idletasks()
        self.root.update()

    def draw_match_outline(
        self: _VisionModeWithHighlighting,
        item_roi: tuple[int, int, int, int],
        should_keep_res: FilterResult,
        locator_result: LocatorResult | None,
    ) -> None:
        reset_canvas(self.root, self.canvas)

        colors = get_filter_colors()
        x, y, w, h, off = self.get_coords_from_roi(item_roi)
        self.canvas.config(height=h, width=w)
        self.create_signal_rect(self.canvas, w, self.thick, colors.matched)

        # show all info strings of the profiles, drawn bottom-up
        text_y = h
        for match in reversed(should_keep_res.matched):
            if missing_affixes := visible_missing_affixes(match.missing_affixes):
                missing_text = f"missing: {', '.join(missing_affixes)}"
                text_y = self.draw_text(self.canvas, missing_text, colors.missing, text_y, 5, w // 2)
            text = match.profile
            if match.set_match:
                text = text + " (incl. Set)"
            text_y = self.draw_text(self.canvas, text, colors.matched, text_y, 5, w // 2)
        # Show matched bullets
        if locator_result and locator_result.reliable and len(should_keep_res.matched) > 0:
            bullet_width = self.thick * 3
            for marker in locator_result.markers:
                self.draw_rect(self.canvas, bullet_width, marker.center, off, colors.matched)

        self.root.geometry(f"{w}x{h}+{x + self.screen_off_x}+{y + self.screen_off_y}")
        self.root.update_idletasks()
        self.root.update()

    def draw_no_match_outline(self: _VisionModeWithHighlighting, item_roi: tuple[int, int, int, int]) -> None:
        reset_canvas(self.root, self.canvas)

        x, y, w, h, _off = self.get_coords_from_roi(item_roi)
        self.canvas.config(height=h, width=w)
        self.create_signal_rect(self.canvas, w, self.thick, get_filter_colors().no_match)
        self.root.geometry(f"{w}x{h}+{x + self.screen_off_x}+{y + self.screen_off_y}")
        self.root.update_idletasks()
        self.root.update()

    def draw_codex_upgrade_outline(
        self: _VisionModeWithHighlighting, item_roi: tuple[int, int, int, int], should_keep_result: FilterResult
    ) -> None:
        reset_canvas(self.root, self.canvas)

        x, y, w, h, _off = self.get_coords_from_roi(item_roi)
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

    def get_coords_from_roi(
        self: _VisionModeWithHighlighting, item_roi: tuple[int, int, int, int]
    ) -> tuple[int, int, int, int, int]:
        x, y, w, h = item_roi
        off = int(w * 0.1)
        x -= off
        y -= off
        w += off * 2
        h += off * 5
        return x, y, w, h, off
