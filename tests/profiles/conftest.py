from typing import TYPE_CHECKING, ClassVar

import pytest
from PyQt6.QtWidgets import QWidget

import src.profiles.editor.profile.tab as profile_tab_module

if TYPE_CHECKING:
    from src.profiles import LoadedProfile, ProfileModel


class FakeSettings:
    """In-memory stand-in for QSettings so tests never touch the user's real profile-editor settings."""

    store: ClassVar[dict[str, bool]] = {}

    def __init__(self, *_args: str) -> None:
        pass

    def value(self, key: str, **kwargs: bool | type[bool]) -> bool:
        return self.store.get(key, kwargs["defaultValue"] is True)

    def setValue(self, key: str, value: bool) -> None:  # noqa: N802 - mirrors the QSettings API
        self.store[key] = value


@pytest.fixture(autouse=True)
def fake_settings(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    FakeSettings.store = {}
    monkeypatch.setattr("src.profiles.pool_controls.greater.QSettings", FakeSettings)
    return FakeSettings.store


class FakeGameCatalog:
    item_types_dict: ClassVar[dict[str, str]] = {}
    affix_dict: ClassVar[dict[str, str]] = {}


class FakeEditor(QWidget):
    def __init__(self, loaded_profile: LoadedProfile, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model: ProfileModel = loaded_profile.profile

    def get_current_model(self) -> ProfileModel:
        return self._model


@pytest.fixture
def fake_tab_editor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ProfileTab's game catalog and editor with lightweight fakes."""
    monkeypatch.setattr(profile_tab_module, "GameCatalog", FakeGameCatalog)
    monkeypatch.setattr(profile_tab_module, "ProfileEditor", FakeEditor)
