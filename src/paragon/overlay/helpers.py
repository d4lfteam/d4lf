"""Small Tk and Windows-DPI helpers used by the Paragon overlay."""

import ctypes
import tkinter as tk
from contextlib import suppress
from typing import TYPE_CHECKING

from src.paragon.overlay.theme import CARD_BG, GOLD, SELECT_BG, TEXT

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.paragon.overlay.contracts import TkOption

TK_BASELINE_SCALING = 96 / 72


def tk_btn(parent: tk.Misc, text: str = "", cmd: Callable[[], None] | None = None, **kw: TkOption) -> tk.Button:
    """Create a pre-styled Tkinter button."""
    opts = {
        "bg": CARD_BG,
        "fg": TEXT,
        "activebackground": SELECT_BG,
        "activeforeground": GOLD,
        "bd": 0,
        "highlightthickness": 0,
    }
    opts.update(kw)
    button = tk.Button(parent, cnf=opts, text=text)
    if cmd is not None:
        button.configure(command=cmd)
    return button


def tk_lbl(parent: tk.Misc, text: str = "", **kw: TkOption) -> tk.Label:
    """Create a pre-styled Tkinter label."""
    opts = {"bg": CARD_BG, "fg": TEXT}
    opts.update(kw)
    return tk.Label(parent, cnf=opts, text=text)


def dpi_scale_for_widget(widget: tk.Misc) -> float:
    """Read the effective DPI scale for a widget, falling back safely."""
    with suppress(Exception):
        return float(ctypes.windll.user32.GetDpiForWindow(int(widget.winfo_id()))) / 96.0
    with suppress(Exception):
        return float(widget.tk.call("tk", "scaling")) * 72 / 96.0
    return 1.0


def measure_build_popup_width(popup: tk.Misc, scale: float) -> int:
    """Return a text-driven width for the floating builds popup.

    The first ``Toplevel`` version still relied on ``winfo_reqwidth()`` from the
    scrollable widget tree. That is not reliable here because the canvas/embedded
    frame can already be width-constrained before the popup geometry is finalized,
    so long build names may report a smaller requested width than their real text
    width. Instead, measure the visible label/button text directly via Tk's font
    engine and then add the known padding, scrollbar, and container margins.
    """
    text_width = 0
    scrollbar_width = 0
    stack: list[tk.Misc] = [popup]

    while stack:
        widget = stack.pop()
        stack.extend(widget.winfo_children())

        with suppress(Exception):
            if isinstance(widget, tk.Scrollbar):
                scrollbar_width = max(scrollbar_width, int(widget.winfo_reqwidth()))
                continue

            if not isinstance(widget, tk.Button | tk.Label):
                continue

            raw_text = str(widget.cget("text") or "")
            if not raw_text:
                continue

            measured = int(widget.tk.call("font", "measure", widget.cget("font"), raw_text))
            padx = int(widget.cget("padx"))
            border = int(widget.cget("bd")) + int(widget.cget("highlightthickness"))

            # Add a small safety buffer so bold glyph overhang and anti-aliased
            # text do not end up visually touching the right edge.
            text_width = max(text_width, measured + (padx * 2) + (border * 2) + int(18 * scale))

    outer_padding = int(24 * scale)
    scrollbar_gap = int(8 * scale) if scrollbar_width else 0
    return max(1, text_width + outer_padding + scrollbar_width + scrollbar_gap)
