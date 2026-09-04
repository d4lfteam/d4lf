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
