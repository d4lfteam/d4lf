import importlib
import os

import pytest

from src.importing.contracts import ImportSession

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from typing import TYPE_CHECKING, Never

from PyQt6.QtWidgets import QApplication

if TYPE_CHECKING:
    from src.type_aliases import JsonValue

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
    store: dict[str, JsonValue] = {}

    class FakeSettings:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def contains(self, key: str) -> bool:
            return key in store

        def value(self, key: str, default: JsonValue = None) -> JsonValue:
            return store.get(key, default)

        def set_value(self, key: str, value: JsonValue) -> None:
            store[key] = value

        def __getattr__(self, name: str):
            methods = {"setValue": self.set_value}
            method = methods.get(name)
            if method is None:
                raise AttributeError(name)
            return method

    monkeypatch.setattr(importer_window_module, "QSettings", FakeSettings)
    return store


def test_filename_part_selector_defaults_to_all_parts(qapp, importer_settings) -> None:
    window = ImporterWindow()
    assert window._selected_filename_parts() == DEFAULT_FILENAME_PARTS
    assert (
        window.filename_parts_summary_label.text() == "Default file name: Source_Season_Class_Build title_Variant.yaml"
    )

    window.close()


def test_importer_window_is_exposed_by_importing_gui_facade() -> None:
    importing_gui = importlib.import_module("src.importing.gui")

    assert importing_gui.ImporterWindow is ImporterWindow


def test_filename_part_selection_persists(qapp, importer_settings) -> None:
    window = ImporterWindow()
    window.filename_part_actions[FilenamePart.CLASS].setChecked(False)
    window.close()
    restored = ImporterWindow()

    assert FilenamePart.CLASS not in restored._selected_filename_parts()

    restored.close()


def test_generate_requires_url_and_filename_parts_or_custom_name(qapp, importer_settings) -> None:
    window = ImporterWindow()
    for action in window.filename_part_actions.values():
        action.setChecked(False)

    window.input_box.setText("https://maxroll.gg/d4/build-guides/example")
    assert not window.generate_button.isEnabled()
    assert window.generate_button.toolTip() == GENERATE_DISABLED_FILENAME_PARTS_TOOLTIP

    window.filename_input_box.setText("my profile")

    assert window.generate_button.isEnabled()

    window.close()


def test_generate_passes_selected_filename_parts(qapp, importer_settings, monkeypatch) -> None:
    captured_config: ImportRequest | None = None

    class FakeThreadPool:
        def start(self, worker) -> None:
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


def test_import_category_choices_persist_and_serialize(qapp, importer_settings, monkeypatch) -> None:
    captured_request: ImportRequest | None = None

    class FakeThreadPool:
        def start(self, worker) -> None:
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


def test_importer_window_accepts_the_composed_accent_color(qapp, importer_settings, monkeypatch) -> None:
    received: list[str] = []
    monkeypatch.setattr(importer_window_module, "set_accent_color", received.append)

    window = ImporterWindow(accent_color="#56B4E9")

    assert received == ["#56B4E9"]
    window.close()


def test_multi_variant_import_cancellation_releases_session(qapp, importer_settings, monkeypatch) -> None:
    class FakeSession:
        name = "fixture"
        closed = False
        close_calls = 0

        def fetch_variants(self, request):
            return []

        def import_build(self, request) -> Never:
            raise AssertionError

        def close(self) -> None:
            self.close_calls += 1
            self.closed = True

    source = FakeSession()
    session = ImportSession(source)
    monkeypatch.setattr(importer_window_module, "open_session", lambda _url: session)
    monkeypatch.setattr(importer_window_module, "select_variants_dialog", lambda *_args: [])
    captured_workers = []

    class FakeThreadPool:
        def start(self, worker) -> None:
            captured_workers.append(worker)

    monkeypatch.setattr(importer_window_module, "THREADPOOL", FakeThreadPool())
    window = ImporterWindow()
    window.multi_build_checkbox.setChecked(True)
    window.input_box.setText("https://maxroll.gg/d4/build-guides/example")
    window._generate_button_click()

    fetch_worker = captured_workers.pop()
    assert fetch_worker.session is session
    window._on_variants_extracted([])

    assert source.close_calls == 1
    window.close()


def test_discovery_failure_releases_session_through_worker(qapp, importer_settings, monkeypatch) -> None:
    class FakeSession:
        name = "fixture"
        close_calls = 0

        def fetch_variants(self, request) -> Never:
            message = "discovery failed"
            raise RuntimeError(message)

        def import_build(self, request) -> Never:
            raise AssertionError

        def close(self) -> None:
            self.close_calls += 1

    source = FakeSession()
    session = ImportSession(source)
    monkeypatch.setattr(importer_window_module, "open_session", lambda _url: session)

    class RunningThreadPool:
        def start(self, worker) -> None:
            worker.run()

    monkeypatch.setattr(importer_window_module, "THREADPOOL", RunningThreadPool())
    window = ImporterWindow()
    window.multi_build_checkbox.setChecked(True)
    window.input_box.setText("https://maxroll.gg/d4/build-guides/example")
    window._generate_button_click()

    assert source.close_calls == 1
    window.close()


def test_import_failure_releases_session_through_worker(qapp, importer_settings) -> None:
    class FakeSource:
        name = "fixture"

        def fetch_variants(self, request):
            return []

        def import_build(self, request) -> Never:
            message = "import failed"
            raise RuntimeError(message)

        def close(self) -> None:
            self.close_calls += 1

        close_calls = 0

    session = ImportSession(FakeSource())
    window = ImporterWindow()
    window._active_import_session = session
    window._waiting_for_user_selection = True
    worker = importer_window_module.ImportWorker(
        request=ImportRequest("https://fixture.invalid/build"), finished=window._on_persist_finished, session=session
    )
    worker.run()

    assert session.closed
    window.close()


def test_selected_variants_receive_the_discovery_session(qapp, importer_settings, monkeypatch) -> None:
    class FakeSession:
        name = "fixture"
        close_calls = 0

        def fetch_variants(self, request):
            return []

        def import_build(self, request) -> Never:
            raise AssertionError

        def close(self) -> None:
            self.close_calls += 1

    source = FakeSession()
    session = ImportSession(source)
    captured_workers = []
    monkeypatch.setattr(importer_window_module, "select_variants_dialog", lambda *_args: ["one"])

    class FakeThreadPool:
        def start(self, worker) -> None:
            captured_workers.append(worker)

    monkeypatch.setattr(importer_window_module, "THREADPOOL", FakeThreadPool())
    window = ImporterWindow()
    window._current_request = ImportRequest(
        "https://maxroll.gg/d4/build-guides/example", options=importing_module.ImportOptions(multi_build=True)
    )
    window._active_import_session = session
    window._on_variants_extracted([])

    assert captured_workers[0].session is session
    window._on_persist_finished()
    assert source.close_calls == 1
    window.close()
