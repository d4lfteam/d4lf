import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.settings.window import ICON_PATH, ConfigWindow


def test_source_mode_icon_path_points_to_repo_asset() -> None:
    expected = Path(__file__).resolve().parents[2] / "assets" / "logo.png"
    assert expected == ICON_PATH
    assert ICON_PATH.is_file()


def test_config_window_can_be_constructed(qapp, isolated_ini_loader) -> None:
    window = ConfigWindow()
    assert window.centralWidget() is not None
    window.close()
