from ._data import *


class OverlayGridMixin(OverlayContract):
    def _update_board_selection(self) -> None:
        """Recolor board cards in-place — no destroy/rebuild, no flicker."""
        for i, card in enumerate(self.board_container.winfo_children()):
            selected = i == self.selected_board_idx
            bg, fg = (SELECT_BG, GOLD) if selected else (CARD_BG, TEXT)
            with suppress(Exception):
                card.configure({"bg": bg})
            for child in card.winfo_children():
                with suppress(Exception):
                    child.configure({"bg": bg, "fg": fg})

    def _select_board_card(self, idx: int) -> None:
        """Select one board card, then redraw and persist the new state."""
        self.selected_board_idx = _clamp_int(idx, 0, max(0, len(self.boards) - 1), 0)
        self._update_board_selection()
        self.redraw()
        self._persist_state()

    def _toggle_collapsed_mode(self) -> None:
        """Switch between the full and compact grid layouts."""
        self._cfg.is_collapsed = not self._cfg.is_collapsed
        with suppress(Exception):
            self.lbl_mode.config(text="Compact View" if self._cfg.is_collapsed else "Full View")
        if is_alive(getattr(self, "btn_view_switch", None)):
            self.btn_view_switch.config(text="⤢" if self._cfg.is_collapsed else "⤡")
        self.redraw()
        self._persist_state()

    def _refresh_lists(self) -> None:
        """Rebuild the board list and refresh the title for the active build."""
        for w in self.board_container.winfo_children():
            w.destroy()

        # The title prefers the profile name. When that is missing, a readable
        # fallback is derived from the build name.
        t = "Paragon"
        if self.builds:
            b = self.builds[self.current_build_idx]
            t = _format_build_display_name(b.get("name"))
            if not t:
                t = _format_build_display_name(b.get("profile"))
        self.lbl_title.config(text=t or "Paragon")

        if not self.boards:
            return
        acc = self._accent_frame_color()

        for idx, bd in enumerate(self.boards):
            txt = format_board_display_text(bd)
            sel = idx == self.selected_board_idx
            bg, fg = (SELECT_BG, GOLD) if sel else (CARD_BG, TEXT)

            c = tk.Frame(
                self.board_container,
                bg=bg,
                highlightthickness=self._accent_frame_thickness(),
                highlightbackground=acc,
                highlightcolor=acc,
            )
            c.pack(fill="x", pady=8)
            lbl = _tk_lbl(
                c,
                text=txt,
                fg=fg,
                bg=bg,
                anchor="w",
                font=("Segoe UI", int(FS_BOARD_CARD * self._cfg.ui_scale), "bold"),
                wraplength=max(200, self._cfg.panel_w - 40),
                justify="left",
            )
            lbl.pack(fill="both", expand=True, padx=14, pady=16)
            lbl.bind("<Button-1>", lambda _e, i=idx: self._select_board_card(i))
            c.bind("<Button-1>", lambda _e, i=idx: self._select_board_card(i))

        self._apply_accent_frames()
        with suppress(Exception):
            self.btn_build_menu.config(state=(tk.NORMAL if len(self.builds) > 1 else tk.DISABLED))

    def _on_boards_mousewheel(self, e: tk.Event) -> None:
        """Scroll the board list on Windows, Linux, and X11 wheel events."""
        delta = (
            -1
            if getattr(e, "delta", 0) > 0 or getattr(e, "num", 0) == 4
            else 1
            if getattr(e, "delta", 0) < 0 or getattr(e, "num", 0) == 5
            else 0
        )
        if delta:
            with suppress(Exception):
                self.boards_canvas.yview_scroll(int(delta), "units")

    def _move_grid(self, dx: int, dy: int) -> None:
        """Move the grid by a small step in the active layout mode."""
        if self._cfg.grid_locked:
            return
        if self._cfg.is_collapsed:
            self.grid_x_collapsed += dx
            self.grid_y_collapsed += dy
        else:
            self.grid_x += dx
            self.grid_y += dy
        self.redraw()
        self._persist_state()

    def _zoom_grid(self, delta: int) -> None:
        """Increase or decrease the active cell size within safe limits."""
        if self._cfg.grid_locked:
            return
        if self._cfg.is_collapsed:
            self._cfg.cell_size_collapsed = max(8, min(50, self._cfg.cell_size_collapsed + delta))
        else:
            self._cfg.cell_size = max(10, min(80, self._cfg.cell_size + delta))
        self.redraw()
        self._persist_state()

    def _on_grid_drag_start(self, e: tk.Event) -> None:
        """Start dragging only when the cursor grabs the outer grid border."""
        self.focus_set()
        if self._cfg.grid_locked or not self._border_rect:
            self._dragging_grid = False
            return
        x1, y1, x2, y2, g, x, y = (*self._border_rect, int(self._border_grab), int(e.x), int(e.y))
        if (
            not (x1 - g <= x <= x2 + g and y1 - g <= y <= y2 + g)
            or min(abs(x - x1), abs(x - x2), abs(y - y1), abs(y - y2)) > g
        ):
            self._dragging_grid = False
            return

        self._dragging_grid, self._drag_start_xy = True, (int(e.x_root), int(e.y_root))
        self._drag_start_grid = (
            (int(self.grid_x_collapsed), int(self.grid_y_collapsed))
            if self._cfg.is_collapsed
            else (int(self.grid_x), int(self.grid_y))
        )

    def _on_grid_drag_move(self, e: tk.Event) -> None:
        """Move the grid live while the user drags the captured border."""
        if not self._dragging_grid:
            return
        dx, dy = (int(e.x_root) - self._drag_start_xy[0], int(e.y_root) - self._drag_start_xy[1])
        if self._cfg.is_collapsed:
            self.grid_x_collapsed, self.grid_y_collapsed = (
                self._drag_start_grid[0] + dx,
                self._drag_start_grid[1] + dy,
            )
        else:
            self.grid_x, self.grid_y = (self._drag_start_grid[0] + dx, self._drag_start_grid[1] + dy)
        self.redraw()

    def _on_grid_drag_end(self, _: tk.Event) -> None:
        """Finish a drag operation and persist the final grid position."""
        if self._dragging_grid:
            self._dragging_grid = False
            self._persist_state()

    def _set_click_through(self, *, enabled: bool) -> None:
        """Set WS_EX_TRANSPARENT style on the window handle to enable/disable click-through.

        Args:
            enabled: True to enable click-through, False to disable it.
        """
        if sys.platform != "win32":
            return

        try:
            hwnd = win32gui.GetAncestor(int(self.winfo_id()), win32con.GA_ROOT)
            styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            new_styles = styles | win32con.WS_EX_TRANSPARENT if enabled else styles & ~win32con.WS_EX_TRANSPARENT
            if new_styles != styles:
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_styles)
                win32gui.SetWindowPos(
                    hwnd,
                    0,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED,
                )
        except tk.TclError, AttributeError, TypeError, ValueError, win32gui.error:
            LOGGER.debug("Failed to set click through style", exc_info=True)

    def _update_click_through(self) -> None:
        """Update click-through style depending on grid lock and mouse position."""
        try:
            if not self._cfg.grid_locked:
                self._set_click_through(enabled=False)
                return

            if not self.winfo_viewable():
                return

            px, py = self.winfo_pointerxy()
            rx = self.winfo_rootx()
            ry = self.winfo_rooty()
            rw = self._cfg.panel_w
            rh = self.winfo_height()

            popup_active = is_alive(getattr(self, "_settings_popup", None), mapped=True) or is_alive(
                getattr(self, "_build_popup", None), mapped=True
            )

            over_panel = (rx <= px < rx + rw) and (ry <= py < ry + rh)
            target_enabled = not (over_panel or popup_active)
            self._set_click_through(enabled=target_enabled)
        except (tk.TclError, AttributeError, ValueError, TypeError) as e:
            LOGGER.debug("Failed to update click-through state: %s", e)

    def _poll_click_through(self) -> None:
        """Poll the click-through state frequently when window is viewable."""
        if self._supports_click_through and is_alive(self):
            self._update_click_through()
            self.after(100, self._poll_click_through)

    def _get_resolution(self) -> tuple[int, int]:
        """Return the tracked game resolution, falling back to the screen size."""
        with suppress(Exception):
            return (int(self._res.resolution[0]), int(self._res.resolution[1]))
        return (self.winfo_screenwidth(), self.winfo_screenheight())

    def _get_cam_roi(self) -> tuple[int, int, int, int] | None:
        """Return the tracked game window ROI when the camera module exposes one."""
        try:
            r = game_window_roi()
            if not r or r.get("width", 0) <= 0:
                return None
            return (int(r["left"]), int(r["top"]), int(r["width"]), int(r["height"]))
        except KeyError, TypeError, ValueError:
            return None

    def _apply_geometry(self) -> None:
        """Resize the overlay to match the tracked game window or full screen."""
        # The floating builds popup is a separate Toplevel, so its screen-space
        # coordinates become stale whenever the tracked game window moves/resizes.
        self._close_build_dropdown()
        roi = self._get_cam_roi()
        rx, ry, rw, rh = roi or (0, 0, *self._get_resolution())
        self.geometry(f"{int(rw)}x{int(rh)}+{int(rx)}+{int(ry)}")
        with suppress(Exception):
            self.canvas.config(width=int(rw), height=int(rh))

    def redraw(self) -> None:
        """Redraw the entire transparent grid overlay for the selected board."""
        self.canvas.delete("all")
        if not self.boards or len(n := self.boards[self.selected_board_idx].nodes) != NODES_LEN:
            return

        grid, acc = nodes_to_grid(n), self._accent_frame_color()
        self._apply_accent_frames()

        cs = int(self._cfg.cell_size_collapsed if self._cfg.is_collapsed else self._cfg.cell_size)
        gx, gy = (
            (int(self.grid_x_collapsed), int(self.grid_y_collapsed))
            if self._cfg.is_collapsed
            else (int(self.grid_x), int(self.grid_y))
        )

        # Compute the square grid size once and reuse it for both the border and
        # the node cell rendering below.
        gpx, bw = GRID * cs, self._grid_frame_thickness()
        bp = max(2, bw)

        self.canvas.create_rectangle(gx - bp, gy - bp, gx + gpx + bp, gy + gpx + bp, outline=acc, width=bw)
        self._border_rect, self._border_grab = (
            (int(gx - bp), int(gy - bp), int(gx + gpx + bp), int(gy + gpx + bp)),
            max(12, (bw * 2) + 2),
        )

        for i in range(GRID + 1):
            p = i * cs
            self.canvas.create_line(gx, gy + p, gx + gpx, gy + p, fill=FS_GRID_COLOR, width=1)
            self.canvas.create_line(gx + p, gy, gx + p, gy + gpx, fill=FS_GRID_COLOR, width=1)

        ins, ow = max(2, cs // 4), max(2, cs // 10)
        for y in range(GRID):
            for x in range(GRID):
                if grid[y][x]:
                    self.canvas.create_rectangle(
                        gx + x * cs + ins,
                        gy + y * cs + ins,
                        gx + (x + 1) * cs - ins,
                        gy + (y + 1) * cs - ins,
                        fill=TRANSPARENT_KEY,
                        outline=acc,
                        width=ow,
                    )
