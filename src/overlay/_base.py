"""Shared full-screen overlay adapter used by the Windows application shell."""

from typing import TYPE_CHECKING

from src.desktop import call_on_ui_thread, create_overlay_toplevel, get_root, join_ui_thread

if TYPE_CHECKING:
    import tkinter as tk


class Overlay:
    """Create the shared transparent Tk surface on the UI thread and run it."""

    def __init__(self):
        self.root: tk.Toplevel
        self.canvas: tk.Canvas

        def build_ui() -> None:
            self.root, self.canvas = create_overlay_toplevel(get_root())
            self.canvas.config(height=self.root.winfo_screenheight(), width=self.root.winfo_screenwidth())

        # Construction can happen from the Qt worker or application thread; Tk owns the UI thread.
        call_on_ui_thread(build_ui)

    def run(self) -> None:
        # Preserve the caller's blocking lifetime while the shared Tk loop owns the thread.
        join_ui_thread()
