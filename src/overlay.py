import logging
from typing import TYPE_CHECKING

from src.desktop import call_on_ui_thread, create_overlay_toplevel, get_root, join_ui_thread

if TYPE_CHECKING:
    import tkinter as tk

LOGGER = logging.getLogger(__name__)


class Overlay:
    def __init__(self):
        self.root: tk.Toplevel
        self.canvas: tk.Canvas

        def _build_ui() -> None:
            self.root, self.canvas = create_overlay_toplevel(get_root())
            self.canvas.config(height=self.root.winfo_screenheight(), width=self.root.winfo_screenwidth())

        # Widget creation must happen on the shared UI thread, not whichever
        # thread constructs this (the BackendWorker QThread, or main() directly).
        call_on_ui_thread(_build_ui)

    def run(self):
        # The shared UI thread owns the one true mainloop now; block here so
        # this caller's thread still tracks Tk's lifetime like it did before.
        join_ui_thread()
