from src.paragon.overlay.theme import BUILD_SOURCES, CARD_BG, GOLD, PANEL_W


def test_theme_exposes_overlay_constants() -> None:
    assert CARD_BG == "#151515"
    assert GOLD == "#cfa15b"
    assert PANEL_W == 370
    assert "maxroll" in BUILD_SOURCES
