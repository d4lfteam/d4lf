from src.overlay.settings import (
    BOOL_DEFAULTS,
    INT_DEFAULTS,
    STR_DEFAULTS,
    STRING_INT_DEFAULTS,
    WB_REFERENCE_DEFAULT,
    InfoSettingValue,
    setting_bool,
    setting_int,
    setting_position,
    setting_str,
    wb_reference,
)


def test_setting_helpers_fall_back_to_shared_defaults_for_wrong_types() -> None:
    values: dict[str, InfoSettingValue] = {
        "font_size": "1",
        "exp_age_before_refresh": None,
        "locked": 1,
        "font_family": 2,
        "wb_reference": "now",
    }
    assert setting_int(values, "font_size") == INT_DEFAULTS["font_size"]
    assert setting_int(values, "exp_age_before_refresh") == STRING_INT_DEFAULTS["exp_age_before_refresh"]
    assert setting_bool(values, "locked") is BOOL_DEFAULTS["locked"]
    assert setting_str(values, "font_family") == STR_DEFAULTS["font_family"]
    assert wb_reference(values) is WB_REFERENCE_DEFAULT
    assert setting_position("(1, 2)") == (1, 2)


def test_setting_helpers_return_stored_values() -> None:
    values: dict[str, InfoSettingValue] = {"x": 7, "show_wb": False, "orientation": "vertical"}
    assert setting_int(values, "x") == 7
    assert setting_bool(values, "show_wb") is False
    assert setting_str(values, "orientation") == "vertical"
