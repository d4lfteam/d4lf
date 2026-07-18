from ._data import *


class OverlayCoreMixin(OverlayContract):
    def __init__(
        self,
        parent: tk.Misc,
        builds: list[BuildRow],
        *,
        cfg: OverlayConfig | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the overlay window, restore settings, and build the UI."""
        super().__init__(parent)
        self._settings: OverlaySettings = _load_overlay_settings()
        self._cfg: OverlayConfig = cfg or OverlayConfig()
        self._on_close: Callable[[], None] | None = on_close
        self._settings_popup: tk.Frame | None = None
        self._settings_popup_refresh: Callable[[], None] | None = None
        self._build_popup: tk.Toplevel | None = None
        self._build_popup_refresh: Callable[[], None] | None = None
        self._settings_popup_escape_bind_id: str | None = None
        self._settings_popup_bind_id: str | None = None
        self._build_popup_bind_id: str | None = None
        self._build_popup_escape_bind_id: str | None = None
        self._warmup_after_id: str | None = None
        self._lock_img_cache: dict[bool, tk.PhotoImage | None]
        self._last_roi: tuple[int, int, int, int] | None
        self._last_res: tuple[int, int] | None
        self._border_rect: tuple[int, int, int, int] | None
        self._dragging_grid: bool = False
        self._border_grab: int = 12
        self._drag_start_xy: tuple[int, int] = (0, 0)
        self._drag_start_grid: tuple[int, int] = (0, 0)
        self._apply_dpi_scaling()

        # Persisted size/position values are trusted only after clamping so a bad
        # INI value cannot create an unusable overlay.
        self._cfg.cell_size = _clamp_int(self._settings.get("cell_size"), 10, 80, self._cfg.cell_size)
        self._cfg.cell_size_collapsed = _clamp_int(
            self._settings.get("cell_size_collapsed"), 8, 50, self._cfg.cell_size_collapsed
        )
        for key, attr in (
            ("is_collapsed", "is_collapsed"),
            ("grid_locked", "grid_locked"),
            ("gold_frames", "gold_frames"),
        ):
            val = self._settings.get(key)
            if isinstance(val, bool):
                setattr(self._cfg, attr, val)

        self._config_loader = get_settings()
        self._config_listener = self._on_config_changed
        self._config_loader.register_change_listener(self._config_listener)
        self._res = get_ui_coordinates()
        self._win_spec = WindowSpec(self._config_loader.advanced_options.process_name)
        self._supports_click_through: bool = sys.platform == "win32"
        self.builds: list[BuildRow] = list(builds)

        # Restore the previously selected build by its persisted identity first.
        # Falling back to profile and then index keeps older settings compatible.
        self.current_build_idx = _resolve_build_index(
            self.builds,
            profile_name=self._settings.get("profile"),
            build_name=self._settings.get("build_name"),
            fallback_idx=self._settings.get("build_idx"),
        )
        self.boards: list[ParagonBoardModel] = self.builds[self.current_build_idx]["boards"] if self.builds else []
        self.selected_board_idx = _clamp_int(self._settings.get("board_idx"), 0, max(0, len(self.boards) - 1), 0)

        gx_val = self._settings.get("grid_x")
        gy_val = self._settings.get("grid_y")
        gxc_val = self._settings.get("grid_x_collapsed")
        gyc_val = self._settings.get("grid_y_collapsed")
        self.grid_x = gx_val if isinstance(gx_val, int) else (self._cfg.panel_w + 24)
        self.grid_y = gy_val if isinstance(gy_val, int) else 24
        self.grid_x_collapsed = gxc_val if isinstance(gxc_val, int) else self._cfg.grid_x_collapsed_default
        self.grid_y_collapsed = gyc_val if isinstance(gyc_val, int) else self._cfg.grid_y_collapsed_default

        self._last_focus_time = time.time()
        (self._last_roi, self._last_res, self._border_rect, self._dragging_grid, self._border_grab) = (
            None,
            None,
            None,
            False,
            12,
        )

        self.title("D4LF Paragon Overlay")
        self.attributes("-topmost", 1)
        with suppress(tk.TclError):
            self.attributes("-alpha", float(self._cfg.window_alpha))
            self.overrideredirect(boolean=True)
            self.wm_attributes("-transparentcolor", TRANSPARENT_KEY)
        self.configure(bg=TRANSPARENT_KEY)
        self.protocol("WM_DELETE_WINDOW", self.close)

        self._build_ui()
        self._bind_events()
        self._apply_geometry()
        self._refresh_lists()
        self.redraw()

        self._warmup_after_id = self.after(600, self._warmup_settings_assets)
        self.after(self._cfg.poll_ms, self._poll_window_state)
        self.after(50, self._poll_close_request)
        if self._supports_click_through:
            self.after(100, self._poll_click_through)
