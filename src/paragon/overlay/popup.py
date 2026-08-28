import tkinter as tk
from contextlib import suppress
from typing import TYPE_CHECKING

from src.desktop import is_alive
from src.paragon.overlay.contracts import OverlayContract
from src.paragon.overlay.theme import CARD_BG, GOLD, TEXT

if TYPE_CHECKING:
    from collections.abc import Callable


class OverlayPopupMixin(OverlayContract):
    def _is_descendant(self, child: tk.Misc, parent: tk.Misc) -> bool:
        """Return True when a widget belongs to the popup subtree."""
        w: tk.Misc | None = child
        while w:
            if w is parent:
                return True
            try:
                w = getattr(w, "master", None)
                if not isinstance(w, tk.Misc):
                    break
            except AttributeError, RuntimeError, tk.TclError:
                break
        return False

    def _close_popup(self, attr_name: str, btn_widget: tk.Button, escape_id_attr: str, click_id_attr: str) -> None:
        """Hide one popup and remove its temporary global event bindings."""
        popup = getattr(self, attr_name, None)
        if isinstance(popup, tk.Frame):
            with suppress(Exception):
                popup.place_forget()
        with suppress(Exception):
            btn_widget.config(fg=TEXT)
        for attr, evt in ((click_id_attr, "<Button-1>"), (escape_id_attr, "<Escape>")):
            if bid := getattr(self, attr, None):
                with suppress(Exception):
                    self.unbind(evt, bid)
                setattr(self, attr, None)

    def _handle_global_click(
        self, e: tk.Event, attr_name: str, btn_widget: tk.Button, close_func: Callable[[], None]
    ) -> None:
        """Close a popup when the user clicks outside of it and its button."""
        popup = getattr(self, attr_name, None)
        if not isinstance(popup, tk.Misc) or not is_alive(popup, mapped=True):
            return
        w: tk.Misc | None = None
        with suppress(Exception):
            w = self.winfo_containing(e.x_root, e.y_root)
        if w is None or (w is not btn_widget and not self._is_descendant(w, popup)):
            close_func()

    def _close_build_dropdown(self) -> None:
        """Destroy the floating builds popup and remove its temporary bindings."""
        popup = self._build_popup
        self._build_popup = None
        self._build_popup_refresh = None

        if popup is not None:
            with suppress(Exception):
                popup.destroy()

        with suppress(Exception):
            self.btn_build_menu.config(fg=TEXT)

        for attr, evt in (("_build_popup_bind_id", "<Button-1>"), ("_build_popup_escape_bind_id", "<Escape>")):
            if bid := getattr(self, attr, None):
                with suppress(Exception):
                    self.unbind(evt, bid)
                setattr(self, attr, None)

    def _close_settings_dropdown(self) -> None:
        """Hide the anchored settings popup and remove its temporary bindings."""
        self._close_popup(
            "_settings_popup", self.btn_settings, "_settings_popup_escape_bind_id", "_settings_popup_bind_id"
        )

    def _show_dropdown(
        self,
        popup_attr: str,
        btn_widget: tk.Button,
        build_func: Callable[[tk.Frame], Callable[[], None]],
        close_func: Callable[[], None],
        escape_attr: str,
        click_attr: str,
        click_handler: Callable[[tk.Event], None],
    ) -> None:
        """Open or close one of the overlay popups and position it near its button.

        This shared helper only manages in-overlay ``Frame`` popups. The builds
        menu now uses its own ``Toplevel`` because it may need more width than the
        overlay itself can provide.
        """
        self._close_build_dropdown()

        popup = getattr(self, popup_attr, None)
        if isinstance(popup, tk.Frame) and is_alive(popup, mapped=True):
            close_func()
            return

        # The settings popup uses lock icons that may be generated lazily.
        # Warm them up once before the popup is shown so the first open feels
        # instant and does not flicker.
        warmup_after_id = self._warmup_after_id
        if warmup_after_id is not None:
            with suppress(Exception):
                self.after_cancel(warmup_after_id)
            self._warmup_after_id = None
        if not hasattr(self, "_lock_img_cache"):
            self._warmup_settings_assets()

        if not isinstance(popup, tk.Frame) or not is_alive(popup):
            c = self._accent_frame_color()
            popup = tk.Frame(
                self,
                bg=CARD_BG,
                bd=0,
                highlightthickness=self._accent_frame_thickness(),
                highlightbackground=c,
                highlightcolor=c,
            )
            setattr(self, popup_attr, popup)
            # The builder returns a refresh callback. We keep that callback so the
            # popup content can be rebuilt later without re-creating the container.
            setattr(self, f"{popup_attr}_refresh", build_func(popup))

        if popup is None:
            return

        self._apply_accent_frames()
        if callable(refresh := getattr(self, f"{popup_attr}_refresh", None)):
            refresh()

        # First place the popup off-screen and let Tk calculate the requested size.
        # This avoids a visible resize flash before we know the final width/height.
        popup.place(x=-9999, y=-9999)
        self.update_idletasks()
        popup.update_idletasks()
        s = self._cfg.ui_scale
        pw = min(max(1, popup.winfo_reqwidth()), max(1, self.winfo_width() - int(8 * s)))
        ph = popup.winfo_reqheight()

        # Start by aligning the popup below the button. If it would overflow the
        # overlay bounds, move it left or above the button instead.
        x, y = (
            btn_widget.winfo_rootx() - self.winfo_rootx(),
            btn_widget.winfo_rooty() - self.winfo_rooty() + btn_widget.winfo_height() + int(4 * s),
        )
        if x + pw > self.winfo_width():
            x = max(0, self.winfo_width() - pw - int(4 * s))
        if y + ph > self.winfo_height():
            y = max(0, btn_widget.winfo_rooty() - self.winfo_rooty() - ph - int(4 * s))

        popup.place(x=x, y=y, width=pw)
        popup.lift()
        with suppress(Exception):
            btn_widget.config(fg=GOLD)

        def _arm() -> None:
            # The global bindings are attached only while the popup is open.
            # Clicking outside or pressing Escape closes the current popup.
            if not getattr(self, click_attr, None):
                setattr(self, click_attr, self.bind("<Button-1>", click_handler, add="+"))
            if not getattr(self, escape_attr, None):
                setattr(self, escape_attr, self.bind("<Escape>", lambda *_: close_func(), add="+"))

        self.after_idle(_arm)

    def _virtual_screen_bounds(self) -> tuple[int, int, int, int]:
        """Return the virtual desktop bounds used for floating popup placement."""
        x = y = 0
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()

        with suppress(Exception):
            x = int(self.winfo_vrootx())
            y = int(self.winfo_vrooty())
            w = int(self.winfo_vrootwidth())
            h = int(self.winfo_vrootheight())

        return x, y, w, h

    def _show_build_menu(self) -> None:
        """Open the floating build selector popup when build data is available."""
        if not self.builds:
            return

        self._close_settings_dropdown()
        popup = self._build_popup
        if popup is not None and is_alive(popup, mapped=True):
            self._close_build_dropdown()
            return

        if popup is None or not is_alive(popup):
            c = self._accent_frame_color()
            popup = tk.Toplevel(self)
            popup.withdraw()
            popup.configure(
                background=CARD_BG,
                bd=0,
                highlightthickness=self._accent_frame_thickness(),
                highlightbackground=c,
                highlightcolor=c,
            )
            with suppress(tk.TclError):
                popup.overrideredirect(boolean=True)
                popup.attributes("-topmost", 1)
            with suppress(Exception):
                popup.transient(self)
            popup.resizable(width=False, height=False)
            popup.bind("<Escape>", lambda *_: self._close_build_dropdown())
            self._build_popup = popup
            self._build_popup_refresh = self._build_build_popup(popup)

        if popup is None:
            return

        self._apply_accent_frames()
        refresh = self._build_popup_refresh
        if refresh is not None:
            refresh()

        popup.update_idletasks()
        s = self._cfg.ui_scale
        margin = int(8 * s)
        popup_width = max(popup.winfo_reqwidth(), self._measure_build_popup_width(popup))
        vx, vy, vw, vh = self._virtual_screen_bounds()
        pw = min(max(1, popup_width), max(1, vw - (margin * 2)))
        ph = popup.winfo_reqheight()

        x = self.btn_build_menu.winfo_rootx()
        y = self.btn_build_menu.winfo_rooty() + self.btn_build_menu.winfo_height() + int(4 * s)

        if x + pw > vx + vw - margin:
            x = max(vx + margin, (vx + vw) - pw - margin)
        x = max(x, vx + margin)
        if y + ph > vy + vh - margin:
            y = max(vy + margin, self.btn_build_menu.winfo_rooty() - ph - int(4 * s))

        popup.geometry(f"{pw}x{ph}+{x}+{y}")
        popup.deiconify()
        popup.lift()
        with suppress(Exception):
            popup.focus_force()
        with suppress(Exception):
            self.btn_build_menu.config(fg=GOLD)

        def _arm() -> None:
            # The overlay keeps the outside-click handler because the popup itself
            # is now a separate window. Escape is bound on both windows so the
            # shortcut still works regardless of which one currently has focus.
            if not getattr(self, "_build_popup_bind_id", None):
                self._build_popup_bind_id = self.bind(
                    "<Button-1>",
                    lambda e: self._handle_global_click(
                        e, "_build_popup", self.btn_build_menu, self._close_build_dropdown
                    ),
                    add="+",
                )
            if not getattr(self, "_build_popup_escape_bind_id", None):
                self._build_popup_escape_bind_id = self.bind(
                    "<Escape>", lambda *_: self._close_build_dropdown(), add="+"
                )

        self.after_idle(_arm)

    def _show_settings_dropdown(self) -> None:
        """Open the settings popup anchored to the settings button."""
        self._show_dropdown(
            "_settings_popup",
            self.btn_settings,
            self._build_settings_popup,
            self._close_settings_dropdown,
            "_settings_popup_escape_bind_id",
            "_settings_popup_bind_id",
            lambda e: self._handle_global_click(e, "_settings_popup", self.btn_settings, self._close_settings_dropdown),
        )
