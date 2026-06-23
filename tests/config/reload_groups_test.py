from src.config.reload_groups import (
    HOTKEY_SETTING_KEYS,
    LOG_LEVEL_SETTING_KEYS,
    VISION_MODE_TYPE_SETTING_KEY,
    has_any_changed,
)


def test_log_level_setting_keys_resolves_to_log_lvl_field():
    assert {"advanced_options.log_lvl"} == LOG_LEVEL_SETTING_KEYS


def test_vision_mode_type_setting_key():
    assert VISION_MODE_TYPE_SETTING_KEY == "general.vision_mode_type"


def test_hotkey_setting_keys_are_namespaced_under_advanced_options():
    assert HOTKEY_SETTING_KEYS
    assert all(key.startswith("advanced_options.") for key in HOTKEY_SETTING_KEYS)


def test_has_any_changed_detects_overlap():
    assert has_any_changed(frozenset({"advanced_options.log_lvl"}), LOG_LEVEL_SETTING_KEYS)


def test_has_any_changed_returns_false_without_overlap():
    assert not has_any_changed(frozenset({"general.language"}), LOG_LEVEL_SETTING_KEYS)
