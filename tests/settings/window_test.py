import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QWidget

import src.settings.window as window_module
from src.settings.window import ICON_PATH, ConfigWindow


def test_source_mode_icon_path_points_to_repo_asset() -> None:
    expected = Path(__file__).resolve().parents[2] / "assets" / "logo.png"
    assert expected == ICON_PATH
    assert ICON_PATH.is_file()


def test_config_window_can_be_constructed(qapp, isolated_ini_loader) -> None:
    window = ConfigWindow()
    assert window.centralWidget() is not None
    window.close()


def test_config_window_restores_maximized_state_from_qsettings(monkeypatch, qapp) -> None:
    class FakeSettings:
        def __init__(self, *_args):
            pass

        def value(self, key, default=None, **kwargs):
            default = kwargs.get("defaultValue", default)
            return True if key == "maximized" else default

    class FakeTab(QWidget):
        def __init__(self, **_kwargs):
            super().__init__()

    maximized = []
    monkeypatch.setattr(window_module, "QSettings", FakeSettings)
    monkeypatch.setattr(window_module, "ConfigTab", FakeTab)
    monkeypatch.setattr(window_module.QMainWindow, "showMaximized", lambda window: maximized.append(window))

    window = ConfigWindow()

    assert maximized == [window]
    window.deleteLater()


def test_config_window_force_maximized_overrides_saved_state(monkeypatch, qapp) -> None:
    class FakeSettings:
        def __init__(self, *_args):
            pass

        def value(self, key, default=None, **kwargs):
            default = kwargs.get("defaultValue", default)
            return False if key == "maximized" else default

    class FakeTab(QWidget):
        def __init__(self, **_kwargs):
            super().__init__()

    maximized = []
    monkeypatch.setattr(window_module, "QSettings", FakeSettings)
    monkeypatch.setattr(window_module, "ConfigTab", FakeTab)
    monkeypatch.setattr(window_module.QMainWindow, "showMaximized", lambda window: maximized.append(window))

    window = ConfigWindow(force_maximized=True)

    assert maximized == [window]
    window.deleteLater()


def test_config_window_persists_maximized_state_on_close(monkeypatch, qapp) -> None:
    class FakeSettings:
        values = {"maximized": False}

        def __init__(self, *_args):
            pass

        def value(self, key, default=None, **kwargs):
            default = kwargs.get("defaultValue", default)
            return self.values.get(key, default)

        def setValue(self, key, value):  # ruff:ignore[invalid-function-name] - mirrors QSettings API
            self.values[key] = value

    class FakeTab(QWidget):
        def __init__(self, **_kwargs):
            super().__init__()

    maximized = False
    monkeypatch.setattr(window_module, "QSettings", FakeSettings)
    monkeypatch.setattr(window_module, "ConfigTab", FakeTab)
    monkeypatch.setattr(ConfigWindow, "isMaximized", lambda _window: maximized)

    window = ConfigWindow()
    maximized = True
    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted()
    assert window.settings.value("maximized") is True

    window.deleteLater()
