from src.overlay.widget import shared as _widget_shared


def test_overlay_shared_colors_are_defined():
    assert _widget_shared.TRANSPARENT_KEY.startswith("#")
    assert _widget_shared.CARD_BG.startswith("#")
