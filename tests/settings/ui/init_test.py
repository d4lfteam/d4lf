from src.settings.ui import ConfigWindow
from src.settings.window import ConfigWindow as Implementation


def test_settings_ui_exposes_window_composition() -> None:
    assert ConfigWindow is Implementation
