import os
from typing import TYPE_CHECKING

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget

import src.profiles.editor.profile.tab as tab_module
import src.profiles.editor.window as window_module
from src.profiles import Loaded, LoadedProfile, ProfileCatalog, ProfileModel, YamlError
from src.profiles.editor import ProfileTab, QSettingsLastOpenedStore

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class FakeDataloader:
    item_types_dict = {}
    affix_dict = {}


class FakeEditor(QWidget):
    def __init__(self, loaded_profile, parent=None):
        super().__init__(parent)
        self._model = loaded_profile.profile

    def get_current_model(self):
        return self._model


class FakeSession:
    def __init__(self, catalog, results, last_opened=None):
        self.catalog = catalog
        self.results = results
        self.last_opened = last_opened

    def discover(self):
        return self.catalog

    def load(self, name):
        result = self.results[name]
        if isinstance(result, list):
            return result.pop(0)
        return result

    def last_opened_profile(self):
        return self.last_opened


def profile(tmp_path: Path, name: str) -> LoadedProfile:
    path = tmp_path / f"{name}.yaml"
    path.write_text("AspectUpgrades:\n- accelerating\n", encoding="utf-8")
    return LoadedProfile(path=path, name=name, profile=ProfileModel(name=name, AspectUpgrades=["accelerating"]))


def make_tab(monkeypatch, qapp, tmp_path, results, names=("alpha", "beta"), initial="alpha"):
    paths = {name: tmp_path / f"{name}.yaml" for name in names}
    catalog = ProfileCatalog(active=list(names), inactive=[], paths=paths)
    session = FakeSession(catalog, results)
    monkeypatch.setattr(tab_module, "Dataloader", FakeDataloader)
    monkeypatch.setattr(tab_module, "ProfileEditor", FakeEditor)
    monkeypatch.setattr(tab_module, "ProfileSession", lambda **_: session)
    return tab_module.ProfileTab(initial_profile_name=initial), session


def test_editor_facade_exports_store():
    assert QSettingsLastOpenedStore.__name__ == "QSettingsLastOpenedStore"
    assert "QSettingsLastOpenedStore" in __import__("src.profiles.editor", fromlist=["__all__"]).__all__
    assert tab_module.QSettingsLastOpenedStore is QSettingsLastOpenedStore


def test_failed_switch_restores_loaded_state_and_combo(monkeypatch, qapp, tmp_path):
    alpha = profile(tmp_path, "alpha")
    results = {"alpha": Loaded(alpha), "beta": YamlError(message="broken")}
    tab, _ = make_tab(monkeypatch, qapp, tmp_path, results)
    editor = tab.model_editor
    tab.load_selected_profile("beta")
    assert tab.current_profile_name == "alpha"
    assert tab.file_path == alpha.path
    assert tab.root is alpha.profile
    assert tab.loaded_profile is alpha
    assert tab.model_editor is editor
    assert tab.profile_combo.currentData() == "alpha"
    tab.load_selected_profile("missing")
    assert tab.current_profile_name == "alpha"
    assert tab.profile_combo.currentData() == "alpha"


def test_refresh_replaces_editor_with_reloaded_profile(monkeypatch, qapp, tmp_path):
    first = profile(tmp_path, "alpha")
    second = profile(tmp_path, "alpha")
    results = {"alpha": [Loaded(first), Loaded(second)], "beta": Loaded(second)}
    tab, _ = make_tab(monkeypatch, qapp, tmp_path, results, names=("alpha",), initial="alpha")
    first_editor = tab.model_editor
    tab.refresh()
    assert tab.model_editor is not first_editor
    assert tab.loaded_profile is second
    assert tab.root is second.profile


def test_initial_profile_is_selected_once_and_unknown_falls_back(monkeypatch, qapp, tmp_path):
    alpha = profile(tmp_path, "alpha")
    beta = profile(tmp_path, "beta")
    results = {"alpha": Loaded(alpha), "beta": Loaded(beta)}
    tab, _ = make_tab(monkeypatch, qapp, tmp_path, results, initial="beta")
    assert tab.current_profile_name == "beta"
    assert tab.loaded_profile is beta

    fallback, _ = make_tab(monkeypatch, qapp, tmp_path, results, names=("alpha",), initial="missing")
    assert fallback.current_profile_name == "alpha"


def test_window_passes_initial_profile_and_close_before_construction(monkeypatch, qapp):
    calls = []

    class FakeTab(QWidget):
        def __init__(self, initial_profile_name=None):
            super().__init__()
            calls.append(initial_profile_name)

        def check_close_save(self):
            return True

    monkeypatch.setattr(window_module, "ProfileTab", FakeTab)
    callbacks = []
    monkeypatch.setattr(window_module.QTimer, "singleShot", lambda _delay, callback: callbacks.append(callback))
    window = window_module.ProfileEditorWindow(profile_name="beta")
    early_event = QCloseEvent()
    window.closeEvent(early_event)
    assert early_event.isAccepted()
    callbacks[0]()
    assert calls == []


def test_window_can_be_forced_maximized_by_parent(monkeypatch, qapp):
    class FakeSettings:
        def __init__(self, *_args):
            pass

        def value(self, key, default=None):
            return False if key == "maximized" else default

    monkeypatch.setattr(window_module, "QSettings", FakeSettings)
    maximized = []
    monkeypatch.setattr(window_module.QMainWindow, "showMaximized", lambda window: maximized.append(window))
    monkeypatch.setattr(window_module.QTimer, "singleShot", lambda *_args: None)

    window = window_module.ProfileEditorWindow(force_maximized=True)

    assert maximized == [window]


@pytest.mark.parametrize(
    ("reply", "accepted"),
    [
        (QMessageBox.StandardButton.Yes, True),
        (QMessageBox.StandardButton.No, True),
        (QMessageBox.StandardButton.Cancel, False),
    ],
)
def test_close_save_yes_no_cancel(monkeypatch, qapp, reply, accepted):
    monkeypatch.setattr(tab_module.QMessageBox, "warning", lambda *_args, **_kwargs: reply)
    tab = ProfileTab.__new__(ProfileTab)
    tab.save_yaml = lambda: None
    assert tab.confirm_discard_changes() is accepted
