from datetime import UTC, datetime

from src.overlay.settings import (
    InfoSettingValue,
    setting_bool,
    setting_datetime,
    setting_int,
    setting_position,
    setting_str,
)


def test_setting_helpers_return_defaults_for_wrong_types() -> None:
    values: dict[str, InfoSettingValue] = {"i": "1", "b": 1, "s": 2, "d": "now"}
    default = datetime(2024, 1, 1, tzinfo=UTC)
    assert setting_int(values, "i", 3) == 3
    assert setting_bool(values, "b", False) is False
    assert setting_str(values, "s", "x") == "x"
    assert setting_datetime(values, "d", default) is default
    assert setting_position("(1, 2)") == (1, 2)
