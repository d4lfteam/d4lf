import tkinter as tk

from src.perception import monitor_to_window

from ._settings import save_settings as save_info_settings
from ._statistics import SessionStats
from ._widget_shared import ACTIVE_GREEN, LOGGER, OverlayContract


class _OverlayActions(OverlayContract):
    def _close_all_submenus(self):
        for key, existing_popup in list(self._open_submenus.items()):
            if existing_popup.winfo_exists():
                existing_popup.destroy()
            del self._open_submenus[key]

    def _toggle_lock(self):
        self.locked = not self.locked
        self._on_lock_changed()
        self._save_settings()

    def _on_lock_changed(self):
        if self.locked:
            self.config(cursor="")

    def _reset_gold_stats(self):
        SessionStats().reset_gold()
        self._gold_initialized = False
        self.update_stats(gph=0, total_gained=0)
        self._repack()

    def _change_font_family(self, new_font_family):
        self.font_family = new_font_family
        for lbl in self.labels_to_resize:
            lbl.config(font=(self.font_family, self.font_size, "bold"))
        self._save_settings()

    def _reset_exp_stats(self):
        SessionStats().reset_exp()
        self._exp_initialized = False
        self.update_stats(eph=0, total_exp=0, t2l="-")
        self._repack()

    def _pick_exp_bar_pos(self):
        """Show a fullscreen overlay to capture the experience bar position via drag."""
        picker = tk.Toplevel(self)
        picker.attributes("-fullscreen", 1)
        picker.attributes("-alpha", 0.5)
        picker.attributes("-topmost", 1)
        picker.config(bg="black", cursor="cross")

        canvas = tk.Canvas(picker, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        msg = "DRAG ACROSS YOUR EXPERIENCE BAR\n(Escape to cancel)"
        canvas.create_text(
            picker.winfo_screenwidth() // 2,
            picker.winfo_screenheight() // 2,
            text=msg,
            font=(self.font_family, 20, "bold"),
            fill=ACTIVE_GREEN,
        )

        start: tuple[int, int] | None = None
        line_id: int | None = None

        def on_press(event: tk.Event) -> None:
            nonlocal start, line_id
            start = (event.x_root, event.y_root)
            line_id = canvas.create_line(event.x, event.y, event.x, event.y, fill=ACTIVE_GREEN, width=3)

        def on_motion(event: tk.Event) -> None:
            if line_id is not None and start is not None:
                canvas.coords(line_id, start[0], start[1], event.x, event.y)

        def on_release(event: tk.Event) -> None:
            if start is None:
                return
            win_start = monitor_to_window(start)
            win_end = monitor_to_window((event.x_root, event.y_root))
            val = f"({int(win_start[0])}, {int(win_start[1])}, {int(win_end[0])}, {int(win_end[1])})"
            save_info_settings({"exp_bar_pos": val})
            self.settings["exp_bar_pos"] = val
            picker.destroy()
            LOGGER.info(f"Custom EXP bar selection set to {val}")

        picker.bind("<Button-1>", on_press)
        picker.bind("<B1-Motion>", on_motion)
        picker.bind("<ButtonRelease-1>", on_release)
        picker.bind("<Escape>", lambda _: picker.destroy())

    def _reset_exp_bar_pos(self):
        """Reset the custom experience bar position to default."""
        save_info_settings({"exp_bar_pos": "None"})
        self.settings["exp_bar_pos"] = None
        LOGGER.info("Experience bar position reset to default calculation")

    def _destroy_settings_popup(self) -> None:
        popup = self._settings_popup
        self._settings_popup = None
        if popup is not None and popup.winfo_exists():
            popup.destroy()

    def _bind_events(self):
        self._recursive_bind_drag(self)

    def _recursive_bind_drag(self, widget: tk.Misc) -> None:
        """Bind drag events to a widget and all its children recursively."""
        widget.bind("<Button-1>", self._start_drag, add="+")
        widget.bind("<B1-Motion>", self._do_drag, add="+")
        widget.bind("<ButtonRelease-1>", self._stop_drag, add="+")
        widget.bind("<Button-3>", self._show_context_menu, add="+")
        for child in widget.winfo_children():
            self._recursive_bind_drag(child)

    def _change_size(self, delta: int) -> None:
        self.font_size = max(8, min(48, self.font_size + delta))
        for lbl in self.labels_to_resize:
            lbl.config(font=(self.font_family, self.font_size, "bold"))
        self._save_settings()

    def _start_drag(self, event):
        if self.locked:
            return
        self._is_dragging = True
        self.config(cursor="fleur")
        # Calculate and store the fixed offset from the window's top-left to the mouse click
        self._drag_offset_x = event.x_root - self.winfo_x()
        self._drag_offset_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        if self.locked or not hasattr(self, "_drag_offset_x"):
            return
        # Set the geometry based on current mouse position minus the original offset
        x = int(event.x_root - self._drag_offset_x)
        y = int(event.y_root - self._drag_offset_y)
        self.geometry(f"+{x}+{y}")

    def _stop_drag(self, event):
        self._is_dragging = False
        self.config(cursor="")
        self._save_settings()
