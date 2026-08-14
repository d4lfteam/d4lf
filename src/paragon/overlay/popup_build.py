import tkinter as tk
from contextlib import suppress
from typing import TYPE_CHECKING

from src.paragon import data as _data
from src.paragon.shared import (
    _TK_IMAGE_ATTRIBUTE,
    CARD_BG,
    FS_BUILDS_MENU,
    FS_HINT,
    FS_SETTINGS_ICON,
    FS_SETTINGS_LABEL,
    FS_ZOOM_BTN,
    GOLD,
    MUTED,
    SELECT_BG,
    TEXT,
    BuildRow,
    OverlayContract,
    _tk_btn,
    _tk_lbl,
)

globals().update({name: getattr(_data, name) for name in _data.__all__})

if TYPE_CHECKING:
    from collections.abc import Callable


class OverlayPopupBuildMixin(OverlayContract):
    def _build_build_popup(self, host: tk.Misc) -> Callable[[], None]:
        """Create the scrollable builds popup and return its refresh callback."""
        scale = self._cfg.ui_scale
        c = tk.Frame(host, bg=CARD_BG, padx=int(12 * scale), pady=int(10 * scale))
        c.pack(fill="both", expand=True)
        max_h = int(360 * scale)

        # Canvas + inner frame is the standard Tk pattern for a scrollable list.
        # The canvas handles scrolling, while the inner frame holds the real widgets.
        cv = tk.Canvas(c, bg=CARD_BG, highlightthickness=0, bd=0, height=max_h)
        cv.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(c, orient="vertical", command=cv.yview)
        sb.pack(side="right", fill="y")
        cv.configure(yscrollcommand=sb.set)
        lf = tk.Frame(cv, bg=CARD_BG)
        wid = cv.create_window((0, 0), window=lf, anchor="nw")

        # Keep the canvas scroll region and embedded frame width synchronized with
        # the real content size.
        lf.bind("<Configure>", lambda *_: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfigure(wid, width=int(e.width)))

        def _ref() -> None:
            # Rebuild the visible list from scratch. This is simple and reliable for
            # the current popup size and allows highlighting/grouping to stay in sync
            # with the current overlay state.
            for w in lf.winfo_children():
                w.destroy()
            grps: dict[str, list[tuple[int, BuildRow]]] = {}
            for i, b in enumerate(self.builds):
                grps.setdefault(str(b.get("profile") or "Ungrouped"), []).append((i, b))
            mul = len(grps) > 1

            for p in sorted(grps):
                if mul:
                    _tk_lbl(
                        lf,
                        text=p,
                        fg=MUTED,
                        font=("Segoe UI", int(FS_BUILDS_MENU * scale), "bold"),
                        anchor="w",
                        padx=int(6 * scale),
                        pady=int(6 * scale),
                    ).pack(fill="x", pady=(int(4 * scale), int(2 * scale)))
                for i, b in grps[p]:
                    act = i == self.current_build_idx
                    _tk_btn(
                        lf,
                        text=str(b.get("name") or "Unknown Build"),
                        cmd=lambda idx=i: (self._select_build(idx), self._close_build_dropdown()),
                        bg=SELECT_BG if act else CARD_BG,
                        fg=GOLD if act else TEXT,
                        anchor="w",
                        padx=int(10 * scale),
                        pady=int(6 * scale),
                        font=("Segoe UI", int(FS_BUILDS_MENU * scale), "bold" if act else "normal"),
                    ).pack(fill="x", pady=int(2 * scale))
                if mul:
                    # A divider line visually separates profile groups without having
                    # to add more nested containers or special spacing logic.
                    tk.Frame(lf, bg=MUTED, height=1).pack(fill="x", pady=int(6 * scale))

            with suppress(Exception):
                host.update_idletasks()
                # Limit popup height so long build lists stay scrollable instead of
                # growing beyond the overlay window.
                cv.configure(height=min(max_h, max(int(120 * scale), lf.winfo_reqheight())))
                cv.yview_moveto(0.0)

        return _ref  # Initial fill is triggered by the shared popup helper.

    def _build_settings_popup(self, host: tk.Frame) -> Callable[[], None]:
        """Create the settings popup and return its refresh callback."""
        s = self._cfg.ui_scale
        c = tk.Frame(host, bg=CARD_BG, padx=int(14 * s), pady=int(10 * s))
        c.pack(fill="both", expand=True)
        imgs: dict[bool, tk.PhotoImage | None] = getattr(self, "_lock_img_cache", {})

        def _row(
            txt: str, img: tk.PhotoImage | None, lbl_txt: str, cmd: Callable[[], None]
        ) -> tuple[tk.Button, tk.Label]:
            """Create one icon/text setting row with a button and description."""
            r = tk.Frame(c, bg=CARD_BG)
            r.pack(fill="x", pady=int(3 * s))
            b = (
                _tk_btn(r, image=img, cmd=cmd, padx=int(6 * s), pady=int(4 * s))
                if img
                else _tk_btn(
                    r,
                    text=txt,
                    cmd=cmd,
                    font=("Segoe UI", int(FS_SETTINGS_ICON * s), "bold"),
                    padx=int(6 * s),
                    pady=int(4 * s),
                )
            )
            if img:
                setattr(b, _TK_IMAGE_ATTRIBUTE, img)
            b.pack(side="left")
            lbl = _tk_lbl(r, text=lbl_txt, font=("Segoe UI", int(FS_SETTINGS_LABEL * s)), anchor="w")
            lbl.pack(side="left", padx=(int(8 * s), int(24 * s)))
            return b, lbl

        btn_lock, lbl_lock = _row(
            "🔒" if self._cfg.grid_locked else "🔓",
            imgs.get(self._cfg.grid_locked),
            "Grid locked",
            lambda: (self._toggle_grid_lock(), _ref()),
        )
        btn_gold, lbl_gold = _row("★", None, "Golden frames", lambda: (self._toggle_gold_frames(), _ref()))
        _row("↻", None, "Reload profiles", self._reload_profiles)
        _row("↺", None, "Reset grid defaults", lambda: (self._reset_grid_defaults(), _ref()))

        tk.Frame(c, bg=MUTED, height=1).pack(fill="x", pady=int(6 * s))

        # Zoom controls change the active cell size for the current mode.
        zr = tk.Frame(c, bg=CARD_BG)
        zr.pack(fill="x", pady=int(3 * s))
        btn_zm = _tk_btn(
            zr,
            text="−",
            cmd=lambda: (self._zoom_grid(-1), _ref()),
            font=("Segoe UI", int(FS_ZOOM_BTN * s), "bold"),
            padx=int(8 * s),
            pady=int(2 * s),
        )
        btn_zm.pack(side="left")
        lbl_cell = _tk_lbl(zr, font=("Segoe UI", int(FS_SETTINGS_LABEL * s), "bold"), width=5, anchor="center")
        lbl_cell.pack(side="left")
        btn_zp = _tk_btn(
            zr,
            text="+",
            cmd=lambda: (self._zoom_grid(1), _ref()),
            font=("Segoe UI", int(FS_ZOOM_BTN * s), "bold"),
            padx=int(8 * s),
            pady=int(2 * s),
        )
        btn_zp.pack(side="left")
        _tk_lbl(zr, text="Grid Zoom", fg=MUTED, font=("Segoe UI", int(FS_SETTINGS_LABEL * s)), anchor="w").pack(
            side="left", padx=(int(8 * s), 0)
        )

        tk.Frame(c, bg=MUTED, height=1).pack(fill="x", pady=int(4 * s))

        # D-pad buttons provide pixel-precise movement without dragging.
        dp = tk.Frame(c, bg=CARD_BG)
        dp.pack(anchor="w", pady=(int(2 * s), int(2 * s)))
        dc = tk.Frame(dp, bg=CARD_BG)
        dc.pack(side="left")
        sp = int(30 * s)

        r0 = tk.Frame(dc, bg=CARD_BG)
        r0.pack()
        tk.Frame(r0, bg=CARD_BG, width=sp, height=1).pack(side="left")
        _tk_btn(
            r0,
            text="↑",
            cmd=lambda: (self._move_grid(0, -1), _ref()),
            font=("Segoe UI", int(FS_SETTINGS_ICON * s), "bold"),
            width=2,
            pady=int(2 * s),
        ).pack(side="left", padx=1, pady=1)
        tk.Frame(r0, bg=CARD_BG, width=sp, height=1).pack(side="left")

        r1 = tk.Frame(dc, bg=CARD_BG)
        r1.pack()
        _tk_btn(
            r1,
            text="←",
            cmd=lambda: (self._move_grid(-1, 0), _ref()),
            font=("Segoe UI", int(FS_SETTINGS_ICON * s), "bold"),
            width=2,
            pady=int(2 * s),
        ).pack(side="left", padx=1, pady=1)
        tk.Frame(r1, bg=CARD_BG, width=sp, height=1).pack(side="left")
        _tk_btn(
            r1,
            text="→",
            cmd=lambda: (self._move_grid(1, 0), _ref()),
            font=("Segoe UI", int(FS_SETTINGS_ICON * s), "bold"),
            width=2,
            pady=int(2 * s),
        ).pack(side="left", padx=1, pady=1)

        r2 = tk.Frame(dc, bg=CARD_BG)
        r2.pack()
        tk.Frame(r2, bg=CARD_BG, width=sp, height=1).pack(side="left")
        _tk_btn(
            r2,
            text="↓",
            cmd=lambda: (self._move_grid(0, 1), _ref()),
            font=("Segoe UI", int(FS_SETTINGS_ICON * s), "bold"),
            width=2,
            pady=int(2 * s),
        ).pack(side="left", padx=1, pady=1)
        tk.Frame(r2, bg=CARD_BG, width=sp, height=1).pack(side="left")

        _tk_lbl(dp, text="Move\nGrid", fg=MUTED, font=("Segoe UI", int(FS_HINT * s)), anchor="w", justify="left").pack(
            side="left", padx=(int(8 * s), 0)
        )
        tk.Frame(c, bg=MUTED, height=1).pack(fill="x", pady=int(6 * s))
        _tk_lbl(
            c,
            text="• Drag frame to move grid\n• D-Pad ↑ ↓ ← → moves grid per click\n• Use − + buttons to zoom\n• Use ★ to make all frames golden\n• Use ↺ to reset to default size/position\n• Use 🔓 to unlock/lock grid",
            fg=MUTED,
            font=("Segoe UI", int(FS_HINT * s)),
            anchor="w",
            justify="left",
            padx=int(4 * s),
            pady=int(6 * s),
        ).pack(fill="x")

        def _ref() -> None:
            """Refresh labels, icons, and enabled states after a setting changes."""
            lk, gd = self._cfg.grid_locked, getattr(self._cfg, "gold_frames", False)
            lock_image = imgs.get(lk)
            if lock_image is not None:
                btn_lock.configure(image=lock_image)
                setattr(btn_lock, _TK_IMAGE_ATTRIBUTE, lock_image)
            else:
                btn_lock.configure(text="🔒" if lk else "🔓", fg=GOLD if lk else TEXT)
            lbl_lock.configure(text="Grid locked" if lk else "Grid unlocked", fg=GOLD if lk else TEXT)
            btn_gold.configure(fg=GOLD if gd else TEXT)
            lbl_gold.configure(text="Golden frames (on)" if gd else "Golden frames (off)", fg=GOLD if gd else TEXT)

            for w in (btn_zm, btn_zp) + tuple(dc.winfo_children()):
                for child in w.winfo_children():
                    if isinstance(child, tk.Button):
                        child.configure({"state": tk.DISABLED if lk else tk.NORMAL, "fg": MUTED if lk else TEXT})

            lbl_cell.configure(
                text=f"{int(self._cfg.cell_size_collapsed if self._cfg.is_collapsed else self._cfg.cell_size)}px",
                fg=MUTED if lk else TEXT,
            )
            with suppress(Exception):
                host.update_idletasks()
                host.lift()
                host.configure({"bg": CARD_BG})

        _ref()
        return _ref
