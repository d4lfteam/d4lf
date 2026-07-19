from src.desktop.themes import DARK_THEME_TEMPLATE, LIGHT_THEME_TEMPLATE


def test_themes_facade_exports_both_templates() -> None:
    assert DARK_THEME_TEMPLATE != LIGHT_THEME_TEMPLATE
