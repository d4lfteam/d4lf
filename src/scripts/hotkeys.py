from __future__ import annotations

from typing import Any

from src.config.models import IS_HOTKEY_KEY, LIVE_RELOAD_GROUP_KEY, AdvancedOptionsModel, GeneralModel


def setting_key(section: str, field_name: str) -> str:
    return f"{section}.{field_name}"


def field_metadata(model_class: type[Any], field_name: str) -> dict[str, Any]:
    return model_class.model_fields[field_name].json_schema_extra or {}


def collect_reload_group_keys(section: str, model_class: type[Any], group_name: str) -> set[str]:
    return {
        setting_key(section, field_name)
        for field_name in model_class.model_fields
        if field_metadata(model_class, field_name).get(LIVE_RELOAD_GROUP_KEY) == group_name
    }


def collect_hotkey_setting_keys() -> set[str]:
    hotkey_keys = {
        setting_key("advanced_options", field_name)
        for field_name in AdvancedOptionsModel.model_fields
        if field_metadata(AdvancedOptionsModel, field_name).get(IS_HOTKEY_KEY) == "True"
    }
    hotkey_keys.update(collect_reload_group_keys("advanced_options", AdvancedOptionsModel, "hotkeys"))
    return hotkey_keys


def has_any_changed(changed_keys: set[str] | frozenset[str], relevant_keys: set[str]) -> bool:
    return any(key in changed_keys for key in relevant_keys)


def build_hotkey_signature(advanced_options: Any) -> tuple[str | bool, ...]:
    return (
        advanced_options.run_vision_mode,
        advanced_options.exit_key,
        advanced_options.toggle_paragon_overlay,
        advanced_options.vision_mode_only,
        advanced_options.run_filter,
        advanced_options.run_filter_drop,
        advanced_options.run_filter_force_refresh,
        advanced_options.force_refresh_only,
        advanced_options.move_to_inv,
        advanced_options.move_to_chest,
    )


HOTKEY_SETTING_KEYS = collect_hotkey_setting_keys()
LANGUAGE_SETTING_KEYS = collect_reload_group_keys("general", GeneralModel, "language")
LOG_LEVEL_SETTING_KEYS = collect_reload_group_keys("advanced_options", AdvancedOptionsModel, "log_level")
MANUAL_RESTART_SETTING_KEYS = collect_reload_group_keys("general", GeneralModel, "restart_app")
VISION_MODE_TYPE_SETTING_KEY = setting_key("general", "vision_mode_type")
