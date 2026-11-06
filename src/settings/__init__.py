"""Public settings capability interface."""

from src.settings.binding import canonicalize_hotkey, normalize_hotkey, validate_hotkey
from src.settings.constants import BASE_DIR, PARAMS_INI
from src.settings.errors import SettingsLoadError
from src.settings.loader import IniConfigLoader, IniConfigLoaderType
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
from src.settings.models.ui import UiOffsetsModel, UiPosModel, UiRoiModel
from src.settings.reload_groups import (
    HOTKEY_SETTING_KEYS,
    LANGUAGE_SETTING_KEYS,
    LOG_LEVEL_SETTING_KEYS,
    MANUAL_RESTART_SETTING_KEYS,
    VISION_MODE_TYPE_SETTING_KEY,
    has_any_changed,
)
from src.settings.scaling import ResManager, ResManagerType
from src.settings.types import SettingValue, Template
from src.settings.validation import check_greater_than_zero


def get_settings() -> IniConfigLoaderType:
    return IniConfigLoader()


def get_ui_coordinates() -> ResManagerType:
    return ResManager()


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
    "IniConfigLoaderType",
    "ItemRefreshType",
    "LogLevels",
    "MoveItemsType",
    "SettingValue",
    "SettingsCategory",
    "SettingsLoadError",
    "Template",
    "ThemeType",
    "UiOffsetsModel",
    "UiPosModel",
    "UiRoiModel",
    "UnfilteredUniquesType",
    "VisionModeType",
    "canonicalize_hotkey",
    "check_greater_than_zero",
    "get_settings",
    "get_ui_coordinates",
    "has_any_changed",
    "normalize_hotkey",
    "validate_hotkey",
]
