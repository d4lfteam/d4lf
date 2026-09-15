from src.paragon.overlay.helpers import dpi_scale_for_widget, tk_btn, tk_lbl


def test_overlay_helpers_expose_tk_factories_and_dpi_fallback() -> None:
    assert callable(tk_btn)
    assert callable(tk_lbl)
    assert callable(dpi_scale_for_widget)
