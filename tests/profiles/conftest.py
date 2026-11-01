from typing import ClassVar

import pytest


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
