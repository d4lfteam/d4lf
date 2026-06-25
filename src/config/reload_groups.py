"""Setting-key collections for live-reload handling.

These helpers translate the live-reload metadata declared on settings models into
the flat ``section.field`` keys emitted by config change events, so multiple parts of
the app (the script handler, the main window) can react to the same setting changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.config.settings_models import IS_HOTKEY_KEY, LIVE_RELOAD_GROUP_KEY, AdvancedOptionsModel, GeneralModel

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet


def _setting_key(section: str, field_name: str) -> str:
    return f"{section}.{field_name}"


def _field_metadata(model_class: type[Any], field_name: str) -> dict[str, Any]:
    return model_class.model_fields[field_name].json_schema_extra or {}


def _collect_reload_group_keys(section: str, model_class: type[Any], group_name: str) -> set[str]:
    return {
        _setting_key(section, field_name)
        for field_name in model_class.model_fields
        if _field_metadata(model_class, field_name).get(LIVE_RELOAD_GROUP_KEY) == group_name
    }


def _collect_hotkey_setting_keys() -> set[str]:
    hotkey_keys = {
        _setting_key("advanced_options", field_name)
        for field_name in AdvancedOptionsModel.model_fields
        if _field_metadata(AdvancedOptionsModel, field_name).get(IS_HOTKEY_KEY) == "True"
    }
    hotkey_keys.update(_collect_reload_group_keys("advanced_options", AdvancedOptionsModel, "hotkeys"))
    return hotkey_keys


def has_any_changed(changed_keys: AbstractSet[str], relevant_keys: set[str]) -> bool:
    return any(key in changed_keys for key in relevant_keys)


HOTKEY_SETTING_KEYS = _collect_hotkey_setting_keys()
LANGUAGE_SETTING_KEYS = _collect_reload_group_keys("general", GeneralModel, "language")
LOG_LEVEL_SETTING_KEYS = _collect_reload_group_keys("advanced_options", AdvancedOptionsModel, "log_level")
MANUAL_RESTART_SETTING_KEYS = _collect_reload_group_keys("general", GeneralModel, "restart_app")
VISION_MODE_TYPE_SETTING_KEY = _setting_key("general", "vision_mode_type")
