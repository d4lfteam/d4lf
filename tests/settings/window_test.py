import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.settings.window import ConfigWindow


def test_config_window_can_be_constructed(qapp, isolated_ini_loader) -> None:
    window = ConfigWindow()
    assert window.centralWidget() is not None
    window.close()
