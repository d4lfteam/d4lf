"""Public settings capability interface.

The facade stays lightweight: platform hotkey backends, image resources, and Qt
widgets are imported only when the corresponding capability operation is used.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from src.settings.errors import ConfigLoadErrorListener, SettingsLoadError
from src.settings.models import GeneralModel
from src.settings.models.core import (
    CATEGORY_KEY,
    CATEGORY_ORDER,
    HIDE_FROM_GUI_KEY,
    IS_HOTKEY_KEY,
    LIVE_RELOAD_GROUP_KEY,
    AdvancedOptionsModel,
    AspectFilterType,
    BrowserType,
    CharModel,
    CosmeticFilterType,
    ItemRefreshType,
    LogLevels,
    MoveItemsType,
    SettingsCategory,
    ThemeType,
    UnfilteredUniquesType,
    VisionModeType,
)
from src.settings.models.ui import ColorsModel, UiOffsetsModel, UiPosModel, UiRoiModel
from src.settings.reload_groups import (
    HOTKEY_SETTING_KEYS,
    LANGUAGE_SETTING_KEYS,
    LOG_LEVEL_SETTING_KEYS,
    MANUAL_RESTART_SETTING_KEYS,
    VISION_MODE_TYPE_SETTING_KEY,
    has_any_changed,
)
from src.settings.types import Template

if TYPE_CHECKING:
    import logging
    from collections.abc import Callable

BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent.parent.parent
PARAMS_INI = "params.ini"


class Settings(Protocol):
    """Typed persistence and reload interface used by other capabilities."""

    @property
    def advanced_options(self) -> AdvancedOptionsModel: ...

    @property
    def char(self) -> CharModel: ...

    @property
    def general(self) -> GeneralModel: ...

    @property
    def user_dir(self) -> Path: ...

    @property
    def config_revision(self) -> int: ...

    def load(self, clear: bool = False, notify: bool = True) -> None: ...

    def reload_if_changed(self) -> bool: ...

    def save_value(self, section: str, key: str, value: object) -> None: ...

    def register_change_listener(self, listener: Callable[[frozenset[str]], None]) -> None: ...

    def unregister_change_listener(self, listener: Callable[[frozenset[str]], None]) -> None: ...

    def register_load_error_listener(self, listener: ConfigLoadErrorListener) -> None: ...

    def unregister_load_error_listener(self, listener: ConfigLoadErrorListener) -> None: ...

    def consume_deferred_cleanup_log_records(self) -> list[logging.LogRecord]: ...


class UiCoordinates(Protocol):
    """Resolution-scaled UI coordinates at the 3840x2160 reference seam."""

    @property
    def offsets(self) -> UiOffsetsModel: ...

    @property
    def pos(self) -> UiPosModel: ...

    @property
    def resolution(self) -> tuple[int, ...]: ...

    @property
    def roi(self) -> UiRoiModel: ...

    @property
    def colors(self) -> ColorsModel: ...

    def set_resolution(self, res: str) -> None: ...

    @property
    def templates(self) -> dict[str, Template]: ...


def get_settings() -> Settings:
    from src.settings.loader import IniConfigLoader  # ruff:ignore[import-outside-top-level]

    return IniConfigLoader()


def get_ui_coordinates() -> UiCoordinates:
    from src.settings.scaling import ResManager  # ruff:ignore[import-outside-top-level]

    return ResManager()


def create_settings_window(*args: object, **kwargs: object) -> object:
    from src.settings.window import ConfigWindow  # ruff:ignore[import-outside-top-level]

    return ConfigWindow(*args, **kwargs)


def validate_hotkey(value: str) -> str:
    from src.settings.hotkeys import validate_hotkey as implementation  # ruff:ignore[import-outside-top-level]

    return implementation(value)


def canonicalize_hotkey(value: str) -> str:
    from src.settings.hotkeys import canonicalize_hotkey as implementation  # ruff:ignore[import-outside-top-level]

    return implementation(value)


def normalize_hotkey(value: str) -> str:
    from src.settings.hotkeys import normalize_hotkey as implementation  # ruff:ignore[import-outside-top-level]

    return implementation(value)


def press(value: str) -> None:
    from src.settings.hotkeys import press as implementation  # ruff:ignore[import-outside-top-level]

    implementation(value)


def release(value: str) -> None:
    from src.settings.hotkeys import release as implementation  # ruff:ignore[import-outside-top-level]

    implementation(value)


def send(value: str) -> None:
    from src.settings.hotkeys import send as implementation  # ruff:ignore[import-outside-top-level]

    implementation(value)


def add_hotkey(hotkey: str, callback: Callable[[], None]) -> int:
    from src.settings.hotkeys import add_hotkey as implementation  # ruff:ignore[import-outside-top-level]

    return implementation(hotkey, callback)


def remove_hotkey(handle: int) -> None:
    from src.settings.hotkeys import remove_hotkey as implementation  # ruff:ignore[import-outside-top-level]

    implementation(handle)


__all__ = [
    "BASE_DIR",
    "CATEGORY_KEY",
    "CATEGORY_ORDER",
    "HIDE_FROM_GUI_KEY",
    "HOTKEY_SETTING_KEYS",
    "IS_HOTKEY_KEY",
    "LANGUAGE_SETTING_KEYS",
    "LIVE_RELOAD_GROUP_KEY",
    "LOG_LEVEL_SETTING_KEYS",
    "MANUAL_RESTART_SETTING_KEYS",
    "PARAMS_INI",
    "VISION_MODE_TYPE_SETTING_KEY",
    "AdvancedOptionsModel",
    "AspectFilterType",
    "BrowserType",
    "CharModel",
    "CosmeticFilterType",
    "GeneralModel",
    "ItemRefreshType",
    "LogLevels",
    "MoveItemsType",
    "Settings",
    "SettingsCategory",
    "SettingsLoadError",
    "Template",
    "ThemeType",
    "UiCoordinates",
    "UiOffsetsModel",
    "UiPosModel",
    "UiRoiModel",
    "UnfilteredUniquesType",
    "VisionModeType",
    "add_hotkey",
    "canonicalize_hotkey",
    "create_settings_window",
    "get_settings",
    "get_ui_coordinates",
    "has_any_changed",
    "normalize_hotkey",
    "press",
    "release",
    "remove_hotkey",
    "send",
    "validate_hotkey",
]
