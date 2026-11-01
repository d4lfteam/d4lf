"""Tk overlay that draws highlighting commands for the current item."""

import logging
import tkinter as tk
from dataclasses import dataclass
from threading import Event
from tkinter.font import Font
from typing import TYPE_CHECKING, override

from src.item import ASPECT_UPGRADES_LABEL
from src.loot.colors import get_filter_colors, reset_canvas, visible_missing_affixes
from src.loot.highlighting.pipeline import (
    CodexUpgradeCommand,
    EmptyOutlineCommand,
    MatchCommand,
    NoMatchCommand,
    RenderingCommand,
)
from src.loot.highlighting.worker import HighlightingWorker
from src.loot.vision_mode import VisionMode
from src.settings import get_settings, get_ui_coordinates

if TYPE_CHECKING:
    import numpy as np

    from src.item import FilterResult, Item
    from src.loot.highlighting.pipeline import ItemRoi, Point
    from src.perception import LocatorResult

LOGGER = logging.getLogger(__name__)

DARK_GRAY_BG = "#111111"
FONT_NAME = "Courier New"
TEXT_OFFSET = 5
# Extra font size per supported window height
FONT_SIZE_BONUS = {1440: 1, 1600: 2, 2160: 3}
# Stipple pattern applied to the signal bars after the given step, the last matching entry wins
SIGNAL_STIPPLES = ((75, "gray75"), (80, "gray50"), (95, "gray25"), (90, "gray12"))


@dataclass(frozen=True)
class ClearCommand:
    """Clear the overlay and set `done` once the canvas is empty."""

    done: Event


type OverlayCommand = RenderingCommand | ClearCommand


def draw_text(canvas: tk.Canvas, text: str, color: str, previous_text_y: int, canvas_center_x: int) -> int:
    """Draw `text` above `previous_text_y` on a dark background and return the top of the drawn text."""
    if not text:
        return previous_text_y

    minimum_font_size = get_settings().general.minimum_overlay_font_size
    window_height = get_ui_coordinates().pos.window_dimensions[1]
    font_size = minimum_font_size + FONT_SIZE_BONUS.get(window_height, 0)

    width_per_character = Font(family=FONT_NAME, size=font_size).measure(text) / len(text)
    if canvas_center_x * 2 // width_per_character < len(text):  # Use a smaller font
        font_size = minimum_font_size
        width_per_character = Font(family=FONT_NAME, size=font_size).measure(text) / len(text)

    text_width = min(int(width_per_character * len(text)), canvas_center_x * 2)
    text_id = canvas.create_text(
        canvas_center_x,
        previous_text_y - TEXT_OFFSET,
        text=text,
        anchor=tk.S,
        font=(FONT_NAME, font_size),
        fill=color,
        width=text_width,
    )
    # Tk wraps at word boundaries, so use the rendered bounds instead of estimating the line count
    x1, y1, x2, y2 = canvas.bbox(text_id)
    background_id = canvas.create_rectangle(x1, y1, x2, y2, fill=DARK_GRAY_BG, outline="")
    canvas.tag_lower(background_id, text_id)
    return y1


def outline_geometry(item_roi: ItemRoi) -> tuple[int, int, int, int, int]:
    """Grow the item ROI to the overlay window as (x, y, width, height, offset)."""
    x, y, w, h = item_roi
    off = int(w * 0.1)
    return x - off, y - off, w + off * 2, h + off * 5, off


class HighlightingVisionMode(VisionMode[OverlayCommand]):
    """Highlights hovered items by evaluating them in a worker and drawing the result on an overlay."""

    def __init__(
        self,
        root: tk.Toplevel,
        canvas: tk.Canvas,
        thick: int,
        screen_offset: Point,
        possible_centers: np.ndarray,
        possible_vendor_centers: np.ndarray,
    ) -> None:
        super().__init__(root, canvas)
        root.geometry("0x0+0+0")
        self.thick = thick
        self.screen_offset = screen_offset
        self.current_item: Item | None = None
        self.worker = HighlightingWorker(self, possible_centers, possible_vendor_centers)

    def clear(self) -> Event:
        """Queue a clear and return an event that is set once the canvas has been cleared."""
        done = Event()
        self.submit(ClearCommand(done))
        return done

    @override
    def on_tts(self, lines: list[str]) -> None:
        self.worker.on_tts(lines)

    @override
    def on_stop(self) -> None:
        self.clear()
        self.worker.stop()

    @override
    def draw(self, command: OverlayCommand) -> None:
        if isinstance(command, ClearCommand):
            reset_canvas(self.root, self.canvas)
            command.done.set()
            return
        if command.item != self.current_item:
            return

        reset_canvas(self.root, self.canvas)
        x, y, w, h, off = outline_geometry(command.item_roi)
        self.canvas.config(height=h, width=w)
        match command:
            case EmptyOutlineCommand(color=color, text=text):
                self._draw_signal_rect(w, color)
                if text is not None:
                    draw_text(self.canvas, text, color, h, w // 2)
            case MatchCommand(filter_result=result, locator_result=locator_result):
                self._draw_match(w, h, off, result, locator_result)
            case NoMatchCommand():
                self._draw_signal_rect(w, get_filter_colors().no_match)
            case CodexUpgradeCommand(filter_result=result):
                self._draw_codex_upgrade(w, h, result)

        self.root.geometry(f"{w}x{h}+{x + self.screen_offset[0]}+{y + self.screen_offset[1]}")
        self.root.update_idletasks()
        self.root.update()

    def _draw_match(self, w: int, h: int, off: int, result: FilterResult, locator_result: LocatorResult | None) -> None:
        colors = get_filter_colors()
        self._draw_signal_rect(w, colors.matched)

        # show all info strings of the profiles, drawn bottom-up
        text_y = h
        for match in reversed(result.matched):
            if missing_affixes := visible_missing_affixes(match.missing_affixes):
                missing_text = f"missing: {', '.join(missing_affixes)}"
                text_y = draw_text(self.canvas, missing_text, colors.missing, text_y, w // 2)
            text = f"{match.profile} (incl. Set)" if match.set_match else match.profile
            text_y = draw_text(self.canvas, text, colors.matched, text_y, w // 2)

        if locator_result and locator_result.reliable and result.matched:
            half_bullet = self.thick * 3 / 2
            for marker in locator_result.markers:
                cx, cy = marker.center[0] + off, marker.center[1] + off
                self.canvas.create_rectangle(
                    int(cx - half_bullet),
                    int(cy - half_bullet),
                    int(cx + half_bullet),
                    int(cy + half_bullet),
                    fill=colors.matched,
                )

    def _draw_codex_upgrade(self, w: int, h: int, result: FilterResult) -> None:
        color = get_filter_colors().codex_upgrade
        self._draw_signal_rect(w, color)
        if len(result.matched) == 1 and result.matched[0].profile == ASPECT_UPGRADES_LABEL:
            draw_text(self.canvas, "Codex Upgrade", color, h, w // 2)
            return
        # This matched an Aspects section in a profile, write the profiles
        text_y = h
        for match in reversed(result.matched):
            text_y = draw_text(self.canvas, match.profile, color, text_y, w // 2)

    def _draw_signal_rect(self, w: int, color: str) -> None:
        thick = self.thick
        self.canvas.create_rectangle(0, 0, w, thick * 2, outline="", fill=color)
        steps = int((thick * 20) / 40)
        for i in range(100):
            stipple = ""
            for after, pattern in SIGNAL_STIPPLES:
                if i > after:
                    stipple = pattern
            start_y = steps * i
            end_y = steps * (i + 1)
            self.canvas.create_rectangle(0, start_y, thick * 2, end_y, fill=color, outline="", stipple=stipple)
            self.canvas.create_rectangle(w - thick * 2, start_y, w, end_y, fill=color, outline="", stipple=stipple)
