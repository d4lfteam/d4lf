import importlib
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # ruff:ignore[unsorted-imports]


importer_window_module = importlib.import_module("src.importing.gui.window")
importing_module = importlib.import_module("src.importing")
DEFAULT_FILENAME_PARTS = importing_module.DEFAULT_FILENAME_PARTS
FilenamePart = importing_module.FilenamePart
ImportRequest = importing_module.ImportRequest
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

        def contains(self, key):
            return key in store

        def value(self, key, default=None):
            return store.get(key, default)

        def setValue(self, key, value):  # ruff:ignore[invalid-function-name]
            store[key] = value

    monkeypatch.setattr(importer_window_module, "QSettings", FakeSettings)
    return store


def test_filename_part_selector_defaults_to_all_parts(qapp, importer_settings):
    window = ImporterWindow()

    assert window._selected_filename_parts() == DEFAULT_FILENAME_PARTS
    assert (
        window.filename_parts_summary_label.text() == "Default file name: Source_Season_Class_Build title_Variant.yaml"
    )

    window.close()


def test_importer_window_is_exposed_by_importing_gui_facade():
    importing_gui = importlib.import_module("src.importing.gui")

    assert importing_gui.ImporterWindow is ImporterWindow


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
    captured_config: ImportRequest | None = None

    class FakeThreadPool:
        def start(self, worker):
            nonlocal captured_config
            captured_config = worker.request

    monkeypatch.setattr(importer_window_module, "THREADPOOL", FakeThreadPool())

    window = ImporterWindow()
    window.filename_part_actions[FilenamePart.SEASON].setChecked(False)
    window.filename_part_actions[FilenamePart.VARIANT].setChecked(False)
    window.input_box.setText("https://maxroll.gg/d4/build-guides/example")

    window._generate_button_click()

    assert captured_config is not None
    assert captured_config.filename_parts == (FilenamePart.SOURCE, FilenamePart.CLASS, FilenamePart.BUILD_TITLE)

    window.close()


def test_import_category_choices_persist_and_serialize(qapp, importer_settings, monkeypatch):
    captured_request: ImportRequest | None = None

    class FakeThreadPool:
        def start(self, worker):
            nonlocal captured_request
            captured_request = worker.request

    monkeypatch.setattr(importer_window_module, "THREADPOOL", FakeThreadPool())

    window = ImporterWindow()
    window.import_charms_checkbox.setChecked(False)
    window.import_seals_checkbox.setChecked(False)
    window.input_box.setText("https://maxroll.gg/d4/build-guides/example")
    window._generate_button_click()

    assert captured_request is not None
    assert not captured_request.options.import_charms
    assert not captured_request.options.import_seals
    window.close()

    restored = ImporterWindow()

    assert not restored.import_charms_checkbox.isChecked()
    assert not restored.import_seals_checkbox.isChecked()
    restored.close()


def test_importer_window_accepts_the_composed_accent_color(qapp, importer_settings, monkeypatch):
    received: list[str] = []
    monkeypatch.setattr(importer_window_module, "set_accent_color", received.append)

    window = ImporterWindow(accent_color="#56B4E9")

    assert received == ["#56B4E9"]
    window.close()
