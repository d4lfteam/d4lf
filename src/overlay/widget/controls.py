import tkinter as tk
from typing import TYPE_CHECKING

from src.loot import get_filter_colors
from src.overlay.settings import save_settings as save_info_settings
from src.overlay.widget.shared import ACCENT, CARD_BG, MUTED, TEXT, OverlayContract

if TYPE_CHECKING:
    from collections.abc import Callable


class _OverlayControls(OverlayContract):
    def _toggle_orientation(self):
        self.orientation = "vertical" if self.orientation == "horizontal" else "horizontal"
        self.overlay_frame.config(highlightbackground=get_filter_colors().matched)
        self._repack()
        self._save_settings()

    def _create_toggle_btn(self, parent, label_text, attr_name, callback=None):
        """Creates a toggle button that updates state and color immediately."""
        is_active = getattr(self, attr_name)
        colors = get_filter_colors()

        btn = tk.Button(
            parent,
            text=label_text,
            bg=CARD_BG,
            fg=colors.matched if is_active else MUTED,
            font=(self.font_family, self.font_size, "bold"),
            activebackground=colors.matched,
            activeforeground=CARD_BG,
            bd=0,
            padx=10,
            pady=5,
            anchor="w",
        )

        def _on_click():
            new_val = not getattr(self, attr_name)
            setattr(self, attr_name, new_val)
            btn.config(fg=colors.matched if new_val else MUTED)
            if callback:
                callback()
            self._repack()
            self._save_settings()

        btn.config(command=_on_click)
        btn.pack(fill="x")
        return btn

    def _create_config_toggle_btn(self, parent, label_text, config_key, callback=None):
        """Creates a toggle button for settings stored in QSettings."""
        is_active = self.settings.get(config_key, False)
        colors = get_filter_colors()

        btn = tk.Button(
            parent,
            text=label_text,
            bg=CARD_BG,
            fg=colors.matched if is_active else MUTED,
            font=(self.font_family, self.font_size, "bold"),
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            bd=0,
            padx=10,
            pady=5,
            anchor="w",
        )

        def _on_click():
            new_val = not self.settings.get(config_key, False)
            save_info_settings({config_key: new_val})
            self.settings[config_key] = new_val
            if callback:
                callback()
            else:
                btn.config(fg=colors.matched if new_val else MUTED)
            self._repack()
            self._save_settings()

        btn.config(command=_on_click)
        btn.pack(fill="x")
        return btn

    def _create_radio_button(
        self, parent, label_text, current_value, target_value, on_select_callback, config_key=None
    ):
        """Creates a radio-style button that visually indicates selection."""
        is_selected = current_value == target_value
        colors = get_filter_colors()
        fg_color = colors.matched if is_selected else MUTED

        btn = tk.Button(
            parent,
            text=f"● {label_text}" if is_selected else f"  {label_text}",
            bg=CARD_BG,
            fg=fg_color,
            font=(self.font_family, self.font_size, "bold"),
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            bd=0,
            padx=20,  # Indent further for radio items
            pady=5,
            anchor="w",
        )

        def _on_click():
            on_select_callback(target_value)
            if config_key:
                save_info_settings({config_key: target_value})
                self.settings[config_key] = target_value
            self._repack()
            self._save_settings()
            # Rebuild the entire popup to update all radio buttons in the group
            self._destroy_settings_popup()
            self._show_context_menu(event=None)  # Re-open at last position

        btn.config(command=_on_click)
        btn.pack(fill="x")
        return btn

    def _create_submenu_button(
        self, parent: tk.Misc, label_text: str, submenu_id: str, content_builder: Callable[[tk.Toplevel], None]
    ):
        """Creates a button that opens a cascading Toplevel submenu to its side."""
        btn = tk.Button(
            parent,
            text=f"{label_text} ▶",  # Default to collapsed
            bg=CARD_BG,
            fg=TEXT,
            font=(self.font_family, self.font_size, "bold"),
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            bd=0,
            padx=10,
            pady=5,
            anchor="w",
            command=lambda: self._open_submenu(btn, submenu_id, content_builder),
        )
        btn.pack(fill="x")
        return btn

    def _on_popup_focus_out(self, event):
        """Delayed check to see if focus left the entire settings UI family."""
        # Tiny delay to allow the new focus widget to be determined by the system
        self.after(100, self._check_popup_focus)

    def _check_popup_focus(self):
        """Destroy popups only if focus has moved entirely out of the settings window family."""
        if not self._settings_popup or not self._settings_popup.winfo_exists():
            return

        focus = self.focus_get()
        if focus:
            # Check if focus is in main popup
            if self._is_descendant(focus, self._settings_popup):
                return
            # Check if focus is in any open submenu
            for sub in self._open_submenus.values():
                if sub.winfo_exists() and self._is_descendant(focus, sub):
                    return

        # Focus is truly gone, cleanup everything
        self._close_all_submenus()
        self._destroy_settings_popup()

    def _open_submenu(self, parent_btn: tk.Button, submenu_id: str, content_builder: Callable[[tk.Toplevel], None]):
        """Opens a cascading Toplevel submenu to the side of the parent button."""
        # Close any other open submenus at this level
        for key, existing_popup in list(self._open_submenus.items()):
            if key != submenu_id and existing_popup.winfo_exists() and existing_popup.master is parent_btn.master:
                existing_popup.destroy()
                del self._open_submenus[key]

        if submenu_id in self._open_submenus and self._open_submenus[submenu_id].winfo_exists():
            # Submenu is already open, close it
            self._open_submenus[submenu_id].destroy()
            del self._open_submenus[submenu_id]
            return

        # Create the submenu
        submenu_popup = tk.Toplevel(parent_btn.master)
        submenu_popup.overrideredirect(boolean=True)
        submenu_popup.attributes("-topmost", 1)
        submenu_popup.configure(bg=CARD_BG, highlightthickness=1, highlightbackground=ACCENT)

        # Build content inside the submenu_popup
        content_builder(submenu_popup)

        # Ensure parent button's geometry is updated before querying its position
        parent_btn.update_idletasks()
        submenu_popup.update_idletasks()

        # Position to the right of the parent button
        x = parent_btn.winfo_rootx() + parent_btn.winfo_width() + 5  # 5 pixels offset to the right
        y = parent_btn.winfo_rooty()

        # Simple boundary check: if it goes off screen to the right, pop to the left
        screen_w = self.winfo_screenwidth()
        if x + submenu_popup.winfo_reqwidth() > screen_w:
            x = parent_btn.winfo_rootx() - submenu_popup.winfo_reqwidth() - 5

        submenu_popup.geometry(f"+{x}+{y}")
        submenu_popup.lift()

        # Bind events
        submenu_popup.bind("<FocusOut>", self._on_popup_focus_out)
        submenu_popup.bind("<Escape>", lambda _: (self._destroy_settings_popup(), self._close_all_submenus()))

        self._open_submenus[submenu_id] = submenu_popup

        # Give focus to the new submenu
        submenu_popup.focus_set()
