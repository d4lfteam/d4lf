import tkinter as tk
from contextlib import suppress

from src.paragon import data as _data
from src.paragon.shared import OverlayContract

globals().update({name: getattr(_data, name) for name in _data.__all__})


class OverlayPopupMixin(OverlayContract):
    def _measure_build_popup_width(self, popup: tk.Misc) -> int:
        """Return a text-driven width for the floating builds popup.

        The first ``Toplevel`` version still relied on ``winfo_reqwidth()`` from the
        scrollable widget tree. That is not reliable here because the canvas/embedded
        frame can already be width-constrained before the popup geometry is finalized,
        so long build names may report a smaller requested width than their real text
        width. Instead, measure the visible label/button text directly via Tk's font
        engine and then add the known padding, scrollbar, and container margins.
        """
        scale = self._cfg.ui_scale
        text_width = 0
        scrollbar_width = 0
        stack: list[tk.Misc] = [popup]

        while stack:
            widget = stack.pop()
            stack.extend(widget.winfo_children())

            with suppress(Exception):
                if isinstance(widget, tk.Scrollbar):
                    scrollbar_width = max(scrollbar_width, int(widget.winfo_reqwidth()))
                    continue

                if not isinstance(widget, tk.Button | tk.Label):
                    continue

                raw_text = str(widget.cget("text") or "")
                if not raw_text:
                    continue

                measured = int(widget.tk.call("font", "measure", widget.cget("font"), raw_text))
                padx = int(widget.cget("padx"))
                border = int(widget.cget("bd")) + int(widget.cget("highlightthickness"))

                # Add a small safety buffer so bold glyph overhang and anti-aliased
                # text do not end up visually touching the right edge.
                text_width = max(text_width, measured + (padx * 2) + (border * 2) + int(18 * scale))

        outer_padding = int(24 * scale)
        scrollbar_gap = int(8 * scale) if scrollbar_width else 0
        return max(1, text_width + outer_padding + scrollbar_width + scrollbar_gap)
