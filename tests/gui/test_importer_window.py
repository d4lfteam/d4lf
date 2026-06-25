import importlib
import os
import sys
import types

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QCheckBox

checkmark_checkbox_module = types.ModuleType("src.gui.models.checkmark_checkbox")
checkmark_checkbox_module.CheckmarkCheckBox = QCheckBox
sys.modules["src.gui.models.checkmark_checkbox"] = checkmark_checkbox_module

importer_window_module = importlib.import_module("src.gui.importer_window")
importer_config_module = importlib.import_module("src.gui.importer.importer_config")
DEFAULT_FILENAME_PARTS = importer_config_module.DEFAULT_FILENAME_PARTS
FilenamePart = importer_config_module.FilenamePart
GENERATE_DISABLED_FILENAME_PARTS_TOOLTIP = importer_window_module.GENERATE_DISABLED_FILENAME_PARTS_TOOLTIP
ImporterWindow = importer_window_module.ImporterWindow


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def importer_settings(monkeypatch):
    store = {}

    class FakeSettings:
        def __init__(self, *args, **kwargs):
            pass

        def value(self, key, default=None):
            return store.get(key, default)

        def setValue(self, key, value):  # noqa: N802
            store[key] = value

    monkeypatch.setattr(importer_window_module, "QSettings", FakeSettings)
    return store


def test_filename_part_selector_defaults_to_all_parts(qapp, importer_settings):
    window = ImporterWindow()

    assert window._selected_filename_parts() == DEFAULT_FILENAME_PARTS
    assert (
        window.filename_parts_summary_label.text() == "Filename parts: Source + Season + Class + Build title + Variant"
    )

    window.close()


def test_filename_part_selection_persists(qapp, importer_settings):
    window = ImporterWindow()
    window.filename_part_actions[FilenamePart.CLASS].setChecked(False)
    window.close()

    restored = ImporterWindow()

    assert FilenamePart.CLASS not in restored._selected_filename_parts()

    restored.close()


def test_generate_requires_url_and_filename_parts_or_custom_name(qapp, importer_settings):
    window = ImporterWindow()
    for action in window.filename_part_actions.values():
        action.setChecked(False)

    window.input_box.setText("https://maxroll.gg/d4/build-guides/example")

    assert not window.generate_button.isEnabled()
    assert window.generate_button.toolTip() == GENERATE_DISABLED_FILENAME_PARTS_TOOLTIP

    window.filename_input_box.setText("my profile")

    assert window.generate_button.isEnabled()

    window.close()


def test_generate_passes_selected_filename_parts(qapp, importer_settings, monkeypatch):
    captured_config = None

    class FakeThreadPool:
        def start(self, worker):
            nonlocal captured_config
            captured_config = worker.kwargs["config"]

    monkeypatch.setattr(importer_window_module, "THREADPOOL", FakeThreadPool())

    window = ImporterWindow()
    window.filename_part_actions[FilenamePart.SEASON].setChecked(False)
    window.filename_part_actions[FilenamePart.VARIANT].setChecked(False)
    window.input_box.setText("https://maxroll.gg/d4/build-guides/example")

    window._generate_button_click()

    assert captured_config.filename_parts == (FilenamePart.SOURCE, FilenamePart.CLASS, FilenamePart.BUILD_TITLE)

    window.close()
