import tkinter as tk

from src.loot import get_filter_colors

from ._settings import setting_int as _setting_int
from ._widget_shared import ACCENT, ACTIVE_GREEN, CARD_BG, MUTED, TEXT, OverlayContract


class _OverlayMenu(OverlayContract):
    def _show_context_menu(self, event):
        """Create and display a persistent settings popup."""
        # Import lazily because lifecycle construction imports this widget.
        # ruff:ignore[import-outside-top-level] - breaks the lifecycle/widget import cycle
        from ._lifecycle import request_close

        self._destroy_settings_popup()

        if event:
            self._last_menu_pos = (event.x_root, event.y_root)

        popup = tk.Toplevel(self)
        popup.overrideredirect(boolean=True)
        popup.attributes("-topmost", 1)
        popup.configure(bg=CARD_BG, highlightthickness=1, highlightbackground=ACCENT)
        self._settings_popup = popup

        # Header
        header = tk.Label(
            popup, text="SETTINGS", bg=ACCENT, fg=CARD_BG, font=(self.font_family, self.font_size, "bold")
        )
        header.pack(fill="x")

        # Visibility Section
        self._create_toggle_btn(popup, "World Boss", "show_wb")
        self._create_toggle_btn(popup, "Legion", "show_legion")
        self._create_toggle_btn(popup, "Helltide", "show_ht")

        tk.Frame(popup, height=1, bg=ACCENT).pack(fill="x", pady=2)

        # Gold Stats Submenu (Cascading)
        def build_gold_submenu_content(submenu_frame):
            def update_dependent_widgets():
                is_tracking = self.capture_gold_stats
                state = tk.NORMAL if is_tracking else tk.DISABLED
                btn_gph.config(state=state, fg=ACTIVE_GREEN if (is_tracking and self.show_gph) else MUTED)
                btn_gained.config(state=state, fg=ACTIVE_GREEN if (is_tracking and self.show_total_gold) else MUTED)

            self._create_toggle_btn(
                submenu_frame, "Track Gold", "capture_gold_stats", callback=update_dependent_widgets
            )

            tk.Frame(submenu_frame, height=1, bg=ACCENT).pack(fill="x", pady=2)

            btn_gph = self._create_toggle_btn(submenu_frame, "Show Gold Per Hour", "show_gph")
            btn_gained = self._create_toggle_btn(submenu_frame, "Show Gold Gained", "show_total_gold")

            update_dependent_widgets()

        self._create_submenu_button(popup, "Gold Config", "gold_stats_submenu", build_gold_submenu_content).pack(
            fill="x"
        )

        # Exp Config Submenu (Cascading)
        def build_exp_submenu_content(submenu_frame):
            def update_dependent_widgets():
                is_tracking = self.capture_exp_stats
                state = tk.NORMAL if is_tracking else tk.DISABLED

                btn_eph.config(state=state, fg=ACTIVE_GREEN if (is_tracking and self.show_eph) else MUTED)
                btn_gained.config(state=state, fg=ACTIVE_GREEN if (is_tracking and self.show_total_exp) else MUTED)
                btn_t2l.config(state=state, fg=ACTIVE_GREEN if (is_tracking and self.show_t2l) else MUTED)
                btn_next.config(state=state, fg=ACTIVE_GREEN if (is_tracking and self.show_next_scan) else MUTED)
                btn_inv.config(
                    state=state,
                    fg=ACTIVE_GREEN if (is_tracking and self.settings.get("check_exp_on_inventory_open")) else MUTED,
                )

                btn_age.config(state=state, fg=TEXT if is_tracking else MUTED)
                btn_pick.config(state=state, fg=TEXT if is_tracking else MUTED)
                btn_reset_pos.config(state=state, fg=TEXT if is_tracking else MUTED)

                if self.settings.get("exp_bar_pos") is None:
                    btn_reset_pos.pack_forget()
                else:
                    btn_reset_pos.pack(fill="x")

            self._create_toggle_btn(submenu_frame, "Track Exp", "capture_exp_stats", callback=update_dependent_widgets)

            tk.Frame(submenu_frame, height=1, bg=ACCENT).pack(fill="x", pady=2)

            btn_eph = self._create_toggle_btn(submenu_frame, "Show EXP Per Hour", "show_eph")
            btn_gained = self._create_toggle_btn(submenu_frame, "Show EXP Gained", "show_total_exp")
            btn_t2l = self._create_toggle_btn(submenu_frame, "Show Time to Level", "show_t2l")
            btn_next = self._create_toggle_btn(submenu_frame, "Show Next Scan", "show_next_scan")

            tk.Frame(submenu_frame, height=1, bg=ACCENT).pack(fill="x", pady=2)

            btn_inv = self._create_config_toggle_btn(
                submenu_frame, "Auto-Capture Exp When Inventory Opened", "check_exp_on_inventory_open"
            )

            def build_exp_age_sub_submenu_content(sub_submenu_frame):
                for label, val in [
                    ("Never", -1),
                    ("0m", 0),
                    ("3m", 3),
                    ("5m", 5),
                    ("10m", 10),
                    ("30m", 30),
                    ("60m", 60),
                ]:
                    self._create_radio_button(
                        sub_submenu_frame,
                        label,
                        _setting_int(self.settings, "exp_age_before_refresh", 5),
                        val,
                        lambda _: None,
                        config_key="exp_age_before_refresh",
                    ).pack(fill="x")

            btn_age = self._create_submenu_button(
                submenu_frame, "EXP Capture Time", "exp_age_sub_submenu", build_exp_age_sub_submenu_content
            )

            tk.Frame(submenu_frame, height=1, bg=ACCENT).pack(fill="x", pady=2)

            btn_pick = tk.Button(
                submenu_frame,
                text="Configure EXP Bar Position",
                bg=CARD_BG,
                fg=TEXT,
                bd=0,
                anchor="w",
                padx=10,
                pady=5,
                font=(self.font_family, self.font_size, "bold"),
                activebackground=ACCENT,
                activeforeground=CARD_BG,
                command=lambda: (self._pick_exp_bar_pos(), self._destroy_settings_popup(), self._close_all_submenus()),
            )
            btn_pick.pack(fill="x")

            btn_reset_pos = tk.Button(
                submenu_frame,
                text="Reset EXP Bar Position",
                bg=CARD_BG,
                fg=TEXT,
                bd=0,
                anchor="w",
                padx=10,
                pady=5,
                font=(self.font_family, self.font_size, "bold"),
                activebackground=ACCENT,
                activeforeground=CARD_BG,
                command=lambda: (self._reset_exp_bar_pos(), self._destroy_settings_popup(), self._close_all_submenus()),
            )
            btn_reset_pos.pack(fill="x")

            update_dependent_widgets()

        self._create_submenu_button(popup, "Exp Config", "exp_stats_submenu", build_exp_submenu_content).pack(fill="x")

        # Reset Stats Submenu (Cascading)
        def build_reset_submenu_content(submenu_frame):
            tk.Button(
                submenu_frame,
                text="Reset Gold",
                bg=CARD_BG,
                fg=TEXT,
                bd=0,
                anchor="w",
                padx=10,
                pady=5,
                font=(self.font_family, self.font_size, "bold"),
                activebackground=ACCENT,
                activeforeground=CARD_BG,
                command=self._reset_gold_stats,
            ).pack(fill="x")
            tk.Button(
                submenu_frame,
                text="Reset Exp",
                bg=CARD_BG,
                fg=TEXT,
                bd=0,
                anchor="w",
                padx=10,
                pady=5,
                font=(self.font_family, self.font_size, "bold"),
                activebackground=ACCENT,
                activeforeground=CARD_BG,
                command=self._reset_exp_stats,
            ).pack(fill="x")

        self._create_submenu_button(popup, "Reset Stats", "reset_stats_submenu", build_reset_submenu_content).pack(
            fill="x"
        )

        tk.Frame(popup, height=1, bg=ACCENT).pack(fill="x", pady=2)

        # UI Adjustments
        tk.Button(
            popup,
            text=f"Orientation: {self.orientation.title()}",
            bg=CARD_BG,
            fg=TEXT,
            bd=0,
            anchor="w",
            padx=10,
            pady=5,
            font=(self.font_family, self.font_size),
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            command=lambda: (
                self._toggle_orientation(),
                self._destroy_settings_popup(),
                self._show_context_menu(event=None),
            ),
        ).pack(fill="x")
        tk.Button(
            popup,
            text="Increase Size (+)",
            bg=CARD_BG,
            fg=TEXT,
            bd=0,
            anchor="w",
            padx=10,
            pady=5,
            font=(self.font_family, self.font_size),
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            command=lambda: (self._change_size(2), self._destroy_settings_popup(), self._show_context_menu(event=None)),
        ).pack(fill="x")
        tk.Button(
            popup,
            text="Decrease Size (-)",
            bg=CARD_BG,
            fg=TEXT,
            bd=0,
            anchor="w",
            padx=10,
            pady=5,
            font=(self.font_family, self.font_size),
            activebackground=ACCENT,
            activeforeground=CARD_BG,
            command=lambda: (
                self._change_size(-2),
                self._destroy_settings_popup(),
                self._show_context_menu(event=None),
            ),
        ).pack(fill="x")

        # Font Submenu
        def build_font_submenu_content(submenu_frame):
            for font_name in self.FONT_CHOICES:
                self._create_radio_button(
                    submenu_frame, font_name, self.font_family, font_name, self._change_font_family
                ).pack(fill="x")

        self._create_submenu_button(popup, "Font", "font_submenu", build_font_submenu_content).pack(fill="x")

        tk.Frame(popup, height=1, bg=ACCENT).pack(fill="x", pady=2)

        # System Actions
        colors = get_filter_colors()
        for label, cmd in [
            ("Refresh Timers Now", self._auto_sync),
            ("Lock Position", self._toggle_lock),
            ("Close Overlay", request_close),
        ]:
            fg_color = TEXT
            if label == "Lock Position" and self.locked:
                fg_color = colors.matched

            btn = tk.Button(
                popup,
                text=label,
                bg=CARD_BG,
                fg=fg_color,
                bd=0,
                anchor="w",
                padx=10,
                pady=5,
                font=(self.font_family, self.font_size),
                activebackground=ACCENT,
                activeforeground=CARD_BG,
                command=lambda c=cmd, lbl=label: (
                    c(),
                    self._destroy_settings_popup(),
                    self._show_context_menu(event=None) if lbl != "Close Overlay" else None,
                ),
            )
            btn.pack(fill="x")
        # Position the popup at the mouse click
        popup.geometry(f"+{self._last_menu_pos[0]}+{self._last_menu_pos[1]}")

        # Auto-close logic
        popup.bind("<FocusOut>", self._on_popup_focus_out)  # Use the family focus out handler
        popup.bind("<Escape>", lambda _: (popup.destroy(), self._close_all_submenus()))  # Escape still closes all
        popup.focus_set()
