from typing import TYPE_CHECKING, override

from src.profiles import ProfileLastOpenedStore

if TYPE_CHECKING:
    from PyQt6.QtCore import QSettings


class QSettingsLastOpenedStore(ProfileLastOpenedStore):
    def __init__(self, settings: QSettings) -> None:
        self._settings = settings

    @override
    def get(self) -> str | None:
        return self._settings.value("last_opened_profile", None, type=str)

    @override
    def set(self, name: str) -> None:
        self._settings.setValue("last_opened_profile", name)
