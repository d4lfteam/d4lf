import time
import tkinter as tk
from contextlib import suppress

from src.automation import is_self_foreground, is_window_foreground
from src.desktop import is_alive, post_to_ui_thread
from src.paragon.data import _clamp_int

# fmt: off
from src.paragon.shared import CARD_BG, FS_BUTTON, FS_CARD_FRAME, FS_GRID_FRAME, FS_MODE_LABEL, FS_PANEL_TITLE, GOLD, LOGGER, MUTED, NODE_BLUE, NODE_GREEN, TRANSPARENT_KEY, OverlayContract, _CLOSE_REQUESTED, _TK_BASELINE_SCALING, _dpi_scale_for_widget, _tk_btn, _tk_lbl  # isort: skip
# fmt: on
from src.paragon import data as _data
from src.settings import get_settings

globals().update({name: getattr(_data, name) for name in _data.__all__})


class OverlayUIMixin(OverlayContract):
    def _apply_dpi_scaling(self) -> None:
        """Apply DPI-aware sizing before widgets are created."""
        with suppress(Exception):
            self.tk.call("tk", "scaling", _TK_BASELINE_SCALING)
        scale = _dpi_scale_for_widget(self) * float(self._cfg.ui_scale or 1.0)
        self._cfg.ui_scale = eff = max(0.75, min(4.0, float(scale)))

        # The panel width always scales with DPI. Cell sizes only scale
        # automatically when the user has not stored an explicit override.
        self._cfg.panel_w = round(self._cfg.panel_w * eff)
        if self._settings.get("cell_size") is None:
            self._cfg.cell_size = round(self._cfg.cell_size * eff)
        if self._settings.get("cell_size_collapsed") is None:
            self._cfg.cell_size_collapsed = round(self._cfg.cell_size_collapsed * eff)

    def _build_ui(self) -> None:
        """Create the left control panel and the transparent drawing canvas."""
        accent = self._accent_frame_color()
        outer = tk.Frame(self, bg=TRANSPARENT_KEY)
        outer.pack(fill="both", expand=True)

        # The canvas owns all grid drawing. The left panel is a separate Frame
        # placed on top of the same transparent outer container.
        self.canvas = tk.Canvas(outer, highlightthickness=0, bg=TRANSPARENT_KEY)
        self.canvas.pack(fill="both", expand=True)

        self.left = tk.Frame(outer, bg=TRANSPARENT_KEY)
        self.left.place(x=0, y=0, width=self._cfg.panel_w, relheight=1.0)

        # Title Card
        self.card_title = tk.Frame(
            self.left,
            bg=CARD_BG,
            highlightthickness=self._accent_frame_thickness(),
            highlightbackground=accent,
            highlightcolor=accent,
        )
        self.card_title.pack(
            fill="x",
            padx=int(10 * self._cfg.ui_scale),
            pady=(int(10 * self._cfg.ui_scale), int(8 * self._cfg.ui_scale)),
        )

        title_row = tk.Frame(self.card_title, bg=CARD_BG)
        title_row.pack(
            fill="both", expand=True, padx=int(12 * self._cfg.ui_scale), pady=(0, int(4 * self._cfg.ui_scale))
        )

        self.lbl_title = _tk_lbl(
            title_row,
            font=("Segoe UI", int(FS_PANEL_TITLE * self._cfg.ui_scale), "bold"),
            anchor="w",
            wraplength=max(200, self._cfg.panel_w - 40),
            justify="left",
        )
        self.lbl_title.pack(side="left", fill="x", expand=True)

        mode_frame = tk.Frame(self.card_title, bg=CARD_BG)
        mode_frame.pack(fill="x", padx=int(12 * self._cfg.ui_scale))

        self.lbl_mode = _tk_lbl(
            mode_frame,
            text="Compact View" if self._cfg.is_collapsed else "Full View",
            fg=MUTED,
            font=("Segoe UI", int(FS_MODE_LABEL * self._cfg.ui_scale)),
            anchor="w",
        )
        self.lbl_mode.pack(side="left")

        self.btn_view_switch = _tk_btn(
            mode_frame,
            text="⤢" if self._cfg.is_collapsed else "⤡",
            cmd=self._toggle_collapsed_mode,
            font=("Segoe UI", int(FS_BUTTON * self._cfg.ui_scale), "bold"),
            padx=int(8 * self._cfg.ui_scale),
            pady=int(2 * self._cfg.ui_scale),
        )
        self.btn_view_switch.pack(side="left", padx=(int(8 * self._cfg.ui_scale), 0))

        # Buttons Card
        self.card_buttons = tk.Frame(
            self.left,
            bg=CARD_BG,
            highlightthickness=self._accent_frame_thickness(),
            highlightbackground=accent,
            highlightcolor=accent,
        )
        self.card_buttons.pack(fill="x", padx=int(10 * self._cfg.ui_scale), pady=(0, int(8 * self._cfg.ui_scale)))

        btn_cont = tk.Frame(self.card_buttons, bg=CARD_BG)
        btn_cont.pack(expand=True, fill="both", padx=int(12 * self._cfg.ui_scale), pady=int(8 * self._cfg.ui_scale))

        self.btn_settings = _tk_btn(
            btn_cont,
            text="Settings⚙ ▼",
            cmd=self._show_settings_dropdown,
            font=("Segoe UI", int(FS_BUTTON * self._cfg.ui_scale), "bold"),
            padx=int(10 * self._cfg.ui_scale),
            pady=int(6 * self._cfg.ui_scale),
        )
        self.btn_settings.pack(side="left", padx=int(4 * self._cfg.ui_scale))

        self.btn_build_menu = _tk_btn(
            btn_cont,
            text="Builds ▼",
            cmd=self._show_build_menu,
            font=("Segoe UI", int(FS_BUTTON * self._cfg.ui_scale), "bold"),
            padx=int(12 * self._cfg.ui_scale),
            pady=int(6 * self._cfg.ui_scale),
        )
        self.btn_build_menu.pack(side="right", padx=int(5 * self._cfg.ui_scale))

        # Boards Scroll Area
        self.boards_canvas = tk.Canvas(self.left, bg=TRANSPARENT_KEY, highlightthickness=0)
        self.boards_canvas.pack(
            fill="both", expand=True, padx=int(10 * self._cfg.ui_scale), pady=(0, int(12 * self._cfg.ui_scale))
        )
        self.board_container = tk.Frame(self.boards_canvas, bg=TRANSPARENT_KEY)
        self._boards_window_id = self.boards_canvas.create_window((0, 0), window=self.board_container, anchor="nw")

        self.board_container.bind(
            "<Configure>", lambda *_: self.boards_canvas.configure(scrollregion=self.boards_canvas.bbox("all"))
        )
        self.boards_canvas.bind(
            "<Configure>", lambda e: self.boards_canvas.itemconfigure(self._boards_window_id, width=int(e.width))
        )

    def _bind_events(self) -> None:
        """Bind scrolling and drag interactions after widgets exist."""
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.boards_canvas.bind(ev, self._on_boards_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self._on_grid_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_grid_drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_grid_drag_end)

    def _poll_close_request(self) -> None:
        """Check for external close requests coming from non-UI threads."""
        if _CLOSE_REQUESTED.is_set():
            _CLOSE_REQUESTED.clear()
            self.close()
            return
        if is_alive(self):
            self.after(50, self._poll_close_request)

    def _poll_window_state(self) -> None:
        """Re-apply geometry when the tracked game window changes size or ROI."""
        try:
            # If we are dragging the grid or interacting with popups, consider it foreground.
            is_interacting = (
                self._dragging_grid
                or is_self_foreground()
                or is_alive(getattr(self, "_settings_popup", None), mapped=True)
                or is_alive(getattr(self, "_build_popup", None), mapped=True)
            )

            is_fgrnd = is_window_foreground(self._win_spec) or is_interacting
            now = time.time()
            if is_fgrnd:
                self._last_focus_time = now

            should_be_visible = is_fgrnd or (now - self._last_focus_time < 0.75)

            if should_be_visible and not self.winfo_viewable():
                self.deiconify()
                self.lift()
            elif not should_be_visible and self.winfo_viewable():
                self.withdraw()

            if not is_fgrnd:
                return

            roi, res = self._get_cam_roi(), self._get_resolution()
            if roi != self._last_roi or res != self._last_res:
                self._last_roi, self._last_res = roi, res
                self._apply_geometry()
                self.redraw()
        finally:
            self.after(self._cfg.poll_ms, self._poll_window_state)

    def _on_config_changed(self, changed_keys: set[str] | frozenset[str]) -> None:
        """Apply live overlay updates after runtime config changes."""
        if "general.colorblind_mode" not in changed_keys:
            return
        post_to_ui_thread(self._apply_live_colorblind_change)

    def _apply_live_colorblind_change(self) -> None:
        """Refresh overlay colors on the Tk UI thread after a colorblind change."""
        if not is_alive(self):
            return
        self._apply_accent_frames(force=True)
        self.redraw()
        LOGGER.info(
            "Applied live Paragon overlay colorblind mode: %s",
            "on" if bool(getattr(self._config_loader.general, "colorblind_mode", False)) else "off",
        )

    def _select_build(self, idx: int) -> None:
        """Activate a build, reset the selected board, and redraw the overlay."""
        if not self.builds:
            return
        self.current_build_idx = _clamp_int(idx, 0, max(0, len(self.builds) - 1), 0)
        self.boards = self.builds[self.current_build_idx]["boards"] if self.builds else []
        self.selected_board_idx = 0
        self._refresh_lists()
        self.redraw()
        self._persist_state()

    def _toggle_grid_lock(self) -> None:
        """Enable or disable all grid movement and zoom controls."""
        self._cfg.grid_locked = not self._cfg.grid_locked
        self._persist_state()
        if self._supports_click_through:
            self._update_click_through()

    def _toggle_gold_frames(self) -> None:
        """Toggle the optional gold accent color override for all frames."""
        self._cfg.gold_frames = not getattr(self._cfg, "gold_frames", False)
        self._persist_state()
        self._apply_accent_frames(force=True)
        self.redraw()

    def _reset_grid_defaults(self) -> None:
        """Restore default grid size and position for both overlay modes."""
        s = float(self._cfg.ui_scale or 1.0)
        self._cfg.cell_size, self._cfg.cell_size_collapsed = (
            _clamp_int(round(24 * s), 10, 80, self._cfg.cell_size),
            _clamp_int(round(16 * s), 8, 50, self._cfg.cell_size_collapsed),
        )
        self.grid_x, self.grid_y = self._cfg.panel_w + round(24 * s), round(24 * s)
        self.grid_x_collapsed, self.grid_y_collapsed = (
            self._cfg.grid_x_collapsed_default,
            self._cfg.grid_y_collapsed_default,
        )
        self._persist_state()
        self.redraw()

    def _accent_frame_color(self) -> str:
        """Resolve the current accent color from settings and colorblind mode."""
        if getattr(self._cfg, "gold_frames", False):
            return GOLD
        try:
            return NODE_BLUE if bool(getattr(get_settings().general, "colorblind_mode", False)) else NODE_GREEN
        except Exception:  # ruff:ignore[blind-except] - preserve color fallback
            LOGGER.debug("Failed to determine Paragon overlay accent color.", exc_info=True)
            return NODE_GREEN

    def _accent_frame_thickness(self) -> int:
        """Return the scaled border width for cards and popup frames."""
        return max(1, round(FS_CARD_FRAME * float(self._cfg.ui_scale or 1.0)))

    def _grid_frame_thickness(self) -> int:
        """Return the scaled outer border width for the rendered node grid."""
        return max(1, round(FS_GRID_FRAME * float(self._cfg.ui_scale or 1.0)))

    def _apply_accent_frames(self, *, force: bool = False) -> None:
        """Refresh accent borders on all existing cards and popups."""
        c = self._accent_frame_color()
        if not force and getattr(self, "_accent_frame_last", None) == c:
            return
        self._accent_frame_last, th = c, self._accent_frame_thickness()

        for w in (getattr(self, "card_title", None), getattr(self, "card_buttons", None)):
            if isinstance(w, tk.Frame) and is_alive(w):
                with suppress(Exception):
                    w.configure(highlightthickness=th, highlightbackground=c, highlightcolor=c)

        bc = getattr(self, "board_container", None)
        if isinstance(bc, tk.Frame) and is_alive(bc):
            for child in bc.winfo_children():
                if isinstance(child, tk.Frame):
                    with suppress(Exception):
                        child.configure(highlightthickness=th, highlightbackground=c, highlightcolor=c)

        for p in ("_settings_popup", "_build_popup"):
            popup = getattr(self, p, None)
            if isinstance(popup, tk.Misc) and is_alive(popup):
                popup.configure(highlightthickness=th, highlightbackground=c, highlightcolor=c)
