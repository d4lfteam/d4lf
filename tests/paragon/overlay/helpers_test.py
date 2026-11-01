from typing import TYPE_CHECKING, cast

from src.paragon.overlay.helpers import dpi_scale_for_widget, measure_build_popup_width, tk_btn, tk_lbl

if TYPE_CHECKING:
    import tkinter as tk


def test_overlay_helpers_expose_tk_factories_and_dpi_fallback() -> None:
    assert callable(tk_btn)
    assert callable(tk_lbl)
    assert callable(dpi_scale_for_widget)


def test_measure_build_popup_width_without_text_widgets_is_only_the_outer_padding() -> None:
    class EmptyPopup:
        def winfo_children(self) -> list[tk.Misc]:
            return []

    assert measure_build_popup_width(cast("tk.Misc", EmptyPopup()), 1.0) == 24
    assert measure_build_popup_width(cast("tk.Misc", EmptyPopup()), 2.0) == 48
