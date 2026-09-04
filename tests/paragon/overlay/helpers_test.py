import pytest

from src.paragon.overlay.helpers import TK_BASELINE_SCALING, dpi_scale_for_widget, tk_btn, tk_lbl


def test_overlay_helpers_expose_tk_factories_and_dpi_fallback() -> None:
    assert pytest.approx(96 / 72) == TK_BASELINE_SCALING
    assert callable(tk_btn)
    assert callable(tk_lbl)
    assert callable(dpi_scale_for_widget)
