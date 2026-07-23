import base64
import io
import tkinter as tk

from PIL import Image, ImageDraw, ImageFont

from src.desktop import is_alive
from src.paragon import data as _data
from src.paragon.shared import OverlayContract

globals().update({name: getattr(_data, name) for name in _data.__all__})


class OverlayGridMixin(OverlayContract):
    def _warmup_settings_assets(self) -> None:
        """Pre-render lock icons so the settings popup opens without image lag."""
        self._warmup_after_id = None
        if not is_alive(self) or hasattr(self, "_lock_img_cache"):
            return
        if is_alive(getattr(self, "_settings_popup", None), mapped=True):
            self._warmup_after_id = self.after(400, self._warmup_settings_assets)
            return

        sz = max(12, int(14 * self._cfg.ui_scale))
        if not Image or not ImageFont or not ImageDraw:
            self._lock_img_cache = {True: None, False: None}
            return

        try:
            # Segoe UI Emoji gives reliable lock/unlock glyphs on Windows and lets
            # the popup use small crisp icons instead of text symbols.
            fnt = ImageFont.truetype(r"C:\Windows\Fonts\seguiemj.ttf", sz)

            def _mk(locked: bool) -> tk.PhotoImage:
                i = Image.new("RGBA", (sz + 2, sz + 2), (0, 0, 0, 0))
                try:
                    ImageDraw.Draw(i).text((1, 1), "🔒" if locked else "🔓", font=fnt, embedded_color=True)
                except TypeError:
                    ImageDraw.Draw(i).text((1, 1), "🔒" if locked else "🔓", font=fnt)
                b = io.BytesIO()
                i.save(b, format="PNG")
                return tk.PhotoImage(master=self, data=base64.b64encode(b.getvalue()))

            self._lock_img_cache = {True: _mk(locked=True), False: _mk(locked=False)}
        except OSError, ValueError, tk.TclError:
            self._lock_img_cache = {True: None, False: None}
