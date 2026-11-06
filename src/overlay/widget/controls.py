import tkinter as tk
from typing import TYPE_CHECKING

from src.loot import get_filter_colors
from src.overlay.settings import InfoSettingValue
from src.overlay.settings import save_settings as save_info_settings
from src.overlay.widget.shared import ACCENT, CARD_BG, MUTED, TEXT, BossTimerContract

if TYPE_CHECKING:
    from collections.abc import Callable


class _OverlayControls(BossTimerContract):
    def _toggle_orientation(self) -> None:
        self.orientation = "vertical" if self.orientation == "horizontal" else "horizontal"
        self.overlay_frame.config(highlightbackground=get_filter_colors().matched)
        self._repack()
        self._save_settings()

    def _create_button(
        self,
        parent: tk.Misc,
        text: str,
        fg: str,
        on_click: Callable[[tk.Button], None],
        *,
        active_bg: str = ACCENT,
        padx: int = 10,
    ) -> tk.Button:
        """Creates and packs a menu button whose click handler receives the button itself."""
        btn = tk.Button(
            parent,
            text=text,
            bg=CARD_BG,
            fg=fg,
            font=(self.font_family, self.font_size, "bold"),
            activebackground=active_bg,
            activeforeground=CARD_BG,
            bd=0,
            padx=padx,
            pady=5,
            anchor="w",
        )
        btn.config(command=lambda: on_click(btn))
        btn.pack(fill="x")
        return btn

    def _create_toggle(
        self,
        parent: tk.Misc,
        label_text: str,
        get_state: Callable[[], bool],
        set_state: Callable[[bool], None],
        callback: Callable[[], None] | None,
        active_bg: str,
    ) -> tk.Button:
        """Creates a toggle button that flips state via the getter/setter pair and recolors immediately."""
        colors = get_filter_colors()

        def _on_click(btn: tk.Button) -> None:
            new_val = not get_state()
            set_state(new_val)
            btn.config(fg=colors.matched if new_val else MUTED)
            if callback:
                callback()
            self._repack()
            self._save_settings()

        fg = colors.matched if get_state() else MUTED
        return self._create_button(parent, label_text, fg, _on_click, active_bg=active_bg)

    def _create_toggle_btn(
        self, parent: tk.Misc, label_text: str, attr_name: str, callback: Callable[[], None] | None = None
    ) -> tk.Button:
        """Creates a toggle button backed by an overlay attribute."""
        return self._create_toggle(
            parent,
            label_text,
            lambda: getattr(self, attr_name),
            lambda value: setattr(self, attr_name, value),
            callback,
            get_filter_colors().matched,
        )

    def _create_config_toggle_btn(self, parent: tk.Misc, label_text: str, config_key: str) -> tk.Button:
        """Creates a toggle button for settings stored in QSettings."""

        def _set(value: bool) -> None:
            save_info_settings({config_key: value})
            self.settings[config_key] = value

        return self._create_toggle(
            parent, label_text, lambda: bool(self.settings.get(config_key, False)), _set, None, ACCENT
        )

    def _create_radio_button(
        self,
        parent: tk.Misc,
        label_text: str,
        current_value: InfoSettingValue,
        target_value: InfoSettingValue,
        on_select_callback: Callable[[InfoSettingValue], None],
        config_key: str | None = None,
    ) -> tk.Button:
        """Creates a radio-style button that visually indicates selection."""
        is_selected = current_value == target_value

        def _on_click(_btn: tk.Button) -> None:
            on_select_callback(target_value)
            if config_key is not None:
                save_info_settings({config_key: target_value})
                self.settings[config_key] = target_value
            self._repack()
            self._save_settings()
            # Rebuild the entire popup to update all radio buttons in the group
            self._destroy_settings_popup()
            self._show_context_menu(event=None)  # Re-open at last position

        return self._create_button(
            parent,
            f"● {label_text}" if is_selected else f"  {label_text}",
            get_filter_colors().matched if is_selected else MUTED,
            _on_click,
            padx=20,  # Indent further for radio items
        )

    def _create_submenu_button(
        self, parent: tk.Misc, label_text: str, submenu_id: str, content_builder: Callable[[tk.Toplevel], None]
    ) -> tk.Button:
        """Creates a button that opens a cascading Toplevel submenu to its side."""
        return self._create_button(
            parent,
            f"{label_text} ▶",  # Default to collapsed
            TEXT,
            lambda btn: self._open_submenu(btn, submenu_id, content_builder),
        )

    def _on_popup_focus_out(self, event: tk.Event) -> None:
        """Delayed check to see if focus left the entire settings UI family."""
        # Tiny delay to allow the new focus widget to be determined by the system
        self.after(100, self._check_popup_focus)

    def _check_popup_focus(self) -> None:
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
                if self._is_descendant(focus, sub):
                    return

        # Focus is truly gone, cleanup everything
        self._close_all_submenus()
        self._destroy_settings_popup()

    def _open_submenu(
        self, parent_btn: tk.Button, submenu_id: str, content_builder: Callable[[tk.Toplevel], None]
    ) -> None:
        """Opens a cascading Toplevel submenu to the side of the parent button."""
        # Close any other open submenus at this level
        for key, existing_popup in list(self._open_submenus.items()):
            if key != submenu_id and existing_popup.winfo_exists() and existing_popup.master is parent_btn.master:
                existing_popup.destroy()
                del self._open_submenus[key]

        if submenu_id in self._open_submenus:
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
