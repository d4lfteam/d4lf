import importlib
import os
from typing import TYPE_CHECKING

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget

import src.profiles.editor.profile.tab as profile_tab_module
from src.profiles import (
    EmptyError,
    Failed,
    Loaded,
    LoadedProfile,
    ProfileCatalog,
    ProfileModel,
    Saved,
    SavedProfile,
    ValidationDiffers,
    ValidationError,
    YamlError,
)
from src.profiles.editor.profile import ProfileTab

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class _FakeGameCatalog:
    item_types_dict = {}
    affix_dict = {}


class _FakeEditor(QWidget):
    def __init__(self, loaded_profile, parent=None):
        super().__init__(parent)
        self._model = loaded_profile.profile

    def get_current_model(self) -> ProfileModel:
        return self._model


class _FakeSession:
    def __init__(self, *, catalog: ProfileCatalog, load_result, save_results=None, dirty=False):
        self._catalog = catalog
        self._load_result = load_result
        self._save_results = list(save_results or [])
        self._dirty = dirty
        self.save_calls: list[tuple[ProfileModel, bool]] = []

    def discover(self) -> ProfileCatalog:
        return self._catalog

    def load(self, name: str):
        return self._load_result

    def save(self, profile_model: ProfileModel, *, force: bool = False):
        self.save_calls.append((profile_model, force))
        return self._save_results.pop(0)

    def is_dirty(self, current_profile_model: ProfileModel) -> bool:
        return self._dirty

    def last_opened_profile(self) -> str | None:
        return None


def _catalog(tmp_path: Path) -> ProfileCatalog:
    path = tmp_path / "profiles" / "alpha.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("AspectUpgrades:\n- accelerating\n", encoding="utf-8")
    return ProfileCatalog(active=["alpha"], inactive=[], paths={"alpha": path})


def _patch_tab_dependencies(monkeypatch, fake_session, tmp_path: Path) -> None:
    monkeypatch.setattr(profile_tab_module, "GameCatalog", _FakeGameCatalog)
    monkeypatch.setattr(profile_tab_module, "ProfileEditor", _FakeEditor)
    monkeypatch.setattr(profile_tab_module, "ProfileSession", lambda **_kwargs: fake_session)


def test_load_validation_guidance_shows_critical(qapp, monkeypatch, tmp_path: Path):
    fake_session = _FakeSession(
        catalog=_catalog(tmp_path), load_result=ValidationError(message="bad", guidance="guidance")
    )
    _patch_tab_dependencies(monkeypatch, fake_session, tmp_path)
    critical_calls = []
    monkeypatch.setattr(
        profile_tab_module.QMessageBox,
        "critical",
        lambda _self, title, message: critical_calls.append((title, message)),
    )

    ProfileTab()

    assert critical_calls == [("Profile Validation Failed", "guidance")]


@pytest.mark.parametrize("load_result", [YamlError(message="broken yaml"), EmptyError(message="empty profile")])
def test_non_validation_load_errors_do_not_show_critical(qapp, monkeypatch, tmp_path: Path, load_result):
    fake_session = _FakeSession(catalog=_catalog(tmp_path), load_result=load_result)
    _patch_tab_dependencies(monkeypatch, fake_session, tmp_path)
    critical_calls = []
    monkeypatch.setattr(profile_tab_module.QMessageBox, "critical", lambda *_args: critical_calls.append(True))

    tab = ProfileTab()

    assert critical_calls == []
    assert tab.model_editor is None


def test_load_validation_without_guidance_shows_validation_error(qapp, monkeypatch, tmp_path: Path):
    fake_session = _FakeSession(catalog=_catalog(tmp_path), load_result=ValidationError(message="validation message"))
    _patch_tab_dependencies(monkeypatch, fake_session, tmp_path)
    critical_calls = []
    monkeypatch.setattr(
        profile_tab_module.QMessageBox,
        "critical",
        lambda _self, title, message: critical_calls.append((title, message)),
    )

    ProfileTab()

    assert critical_calls == [("Validation Error", "validation message")]


def test_save_validation_differs_retries_with_force_and_emits_signal(qapp, monkeypatch, tmp_path: Path):
    loaded_profile = LoadedProfile(
        path=tmp_path / "profiles" / "alpha.yaml",
        name="alpha",
        profile=ProfileModel(name="alpha", AspectUpgrades=["accelerating"]),
    )
    coerced_model = ProfileModel(name="alpha", AspectUpgrades=["accelerating", "snowveiled"])
    fake_session = _FakeSession(
        catalog=_catalog(tmp_path),
        load_result=Loaded(loaded_profile=loaded_profile),
        save_results=[
            ValidationDiffers(coerced_model=coerced_model),
            Saved(saved=SavedProfile(path=loaded_profile.path, file_name="alpha")),
        ],
    )
    _patch_tab_dependencies(monkeypatch, fake_session, tmp_path)
    monkeypatch.setattr(
        profile_tab_module.QMessageBox, "warning", lambda *_args, **_kwargs: QMessageBox.StandardButton.Save
    )
    monkeypatch.setattr(profile_tab_module.QMessageBox, "information", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(profile_tab_module.QMessageBox, "critical", lambda *_args, **_kwargs: None)

    tab = ProfileTab()
    emitted = []
    tab.profile_saved.connect(emitted.append)
    tab.save_yaml()

    assert fake_session.save_calls == [(loaded_profile.profile, False), (coerced_model, True)]
    assert emitted == ["alpha"]


def test_save_saved_shows_info_and_emits_signal(qapp, monkeypatch, tmp_path: Path):
    loaded_profile = LoadedProfile(
        path=tmp_path / "profiles" / "alpha.yaml",
        name="alpha",
        profile=ProfileModel(name="alpha", AspectUpgrades=["accelerating"]),
    )
    fake_session = _FakeSession(
        catalog=_catalog(tmp_path),
        load_result=Loaded(loaded_profile=loaded_profile),
        save_results=[Saved(saved=SavedProfile(path=loaded_profile.path, file_name="alpha"))],
    )
    _patch_tab_dependencies(monkeypatch, fake_session, tmp_path)
    info_calls = []
    monkeypatch.setattr(
        profile_tab_module.QMessageBox, "information", lambda _self, title, message: info_calls.append((title, message))
    )

    tab = ProfileTab()
    emitted = []
    tab.profile_saved.connect(emitted.append)
    tab.save_yaml()

    assert emitted == ["alpha"]
    assert info_calls == [("Info", "Profile saved successfully to alpha.yaml")]


def test_save_failed_shows_critical(qapp, monkeypatch, tmp_path: Path):
    loaded_profile = LoadedProfile(
        path=tmp_path / "profiles" / "alpha.yaml",
        name="alpha",
        profile=ProfileModel(name="alpha", AspectUpgrades=["accelerating"]),
    )
    fake_session = _FakeSession(
        catalog=_catalog(tmp_path),
        load_result=Loaded(loaded_profile=loaded_profile),
        save_results=[Failed(error=RuntimeError("boom"))],
    )
    _patch_tab_dependencies(monkeypatch, fake_session, tmp_path)
    critical_calls = []
    monkeypatch.setattr(
        profile_tab_module.QMessageBox,
        "critical",
        lambda _self, title, message: critical_calls.append((title, message)),
    )

    ProfileTab().save_yaml()

    assert critical_calls == [("Error", "Failed to save profile: boom")]


def test_check_close_save_uses_session_dirty(qapp, monkeypatch, tmp_path: Path):
    loaded_profile = LoadedProfile(
        path=tmp_path / "profiles" / "alpha.yaml",
        name="alpha",
        profile=ProfileModel(name="alpha", AspectUpgrades=["accelerating"]),
    )
    fake_session = _FakeSession(
        catalog=_catalog(tmp_path), load_result=Loaded(loaded_profile=loaded_profile), dirty=True
    )
    _patch_tab_dependencies(monkeypatch, fake_session, tmp_path)

    tab = ProfileTab()
    monkeypatch.setattr(tab, "confirm_discard_changes", lambda: False)

    assert tab.check_close_save() is False


def test_profile_tab_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.profile.tab")
    assert hasattr(module, "ProfileTab")
