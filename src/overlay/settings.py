from datetime import UTC, datetime
from typing import Final, TypeVar

from PyQt6.QtCore import QSettings

type InfoSettingValue = int | str | bool | tuple[int, ...] | datetime | None
T = TypeVar("T", int, str, bool)

_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

INT_DEFAULTS: Final[dict[str, int]] = {"x": 100, "y": 100, "font_size": 14}
STRING_INT_DEFAULTS: Final[dict[str, int]] = {
    "exp_age_before_refresh": 5,
    "session_total_gold": 0,
    "session_total_exp": 0,
}
STR_DEFAULTS: Final[dict[str, str]] = {
    "font_family": "Consolas",
    "orientation": "horizontal",
    "next_boss_name": "Unknown",
}
BOOL_DEFAULTS: Final[dict[str, bool]] = {
    "show_wb": True,
    "show_legion": True,
    "show_ht": True,
    "show_gold": True,
    "show_gph": True,
    "show_total_gold": True,
    "show_exp": True,
    "show_eph": True,
    "show_total_exp": True,
    "show_t2l": True,
    "show_next_scan": True,
    "locked": False,
    "capture_gold_stats": False,
    "capture_exp_stats": False,
    "check_exp_on_inventory_open": True,
}
WB_REFERENCE_DEFAULT: Final = datetime(2024, 1, 1, tzinfo=UTC)


def load_settings() -> dict[str, InfoSettingValue]:
    store = QSettings("d4lf", "InfoOverlay")

    def value(key: str, default: T, kind: type[T]) -> T:
        result = store.value(key, default, type=kind)
        return result if isinstance(result, kind) else default

    def integer(key: str, default: int) -> int:
        try:
            return int(store.value(key, str(default), type=str))
        except TypeError, ValueError:
            return default

    def flag(key: str, *, default: bool) -> bool:
        return value(key, default, bool)

    def position(key: str) -> tuple[int, ...] | None:
        raw = store.value(key, None, type=str)
        if not raw or raw.lower() == "none":
            return None
        try:
            return tuple(int(part.strip()) for part in raw.strip("()").replace(",", " ").split())
        except ValueError:
            return None

    result: dict[str, InfoSettingValue] = {key: value(key, default, int) for key, default in INT_DEFAULTS.items()}
    result.update({key: value(key, default, str) for key, default in STR_DEFAULTS.items()})
    result.update({key: flag(key, default=default) for key, default in BOOL_DEFAULTS.items()})
    result.update({key: integer(key, default) for key, default in STRING_INT_DEFAULTS.items()})
    result["exp_bar_pos"] = position("exp_bar_pos")
    raw_reference = store.value("wb_reference", WB_REFERENCE_DEFAULT.strftime(_DATETIME_FORMAT), type=str)
    try:
        result["wb_reference"] = datetime.strptime(raw_reference, _DATETIME_FORMAT).replace(tzinfo=UTC)
    except TypeError, ValueError:
        result["wb_reference"] = WB_REFERENCE_DEFAULT
    return result


def save_settings(values: dict[str, InfoSettingValue]) -> None:
    store = QSettings("d4lf", "InfoOverlay")
    for key, raw_value in values.items():
        value = raw_value
        if key == "wb_reference" and isinstance(raw_value, datetime):
            value = raw_value.strftime(_DATETIME_FORMAT)
        elif key == "exp_bar_pos":
            value = str(value) if value is not None else "None"
        store.setValue(key, value)


def setting_int(values: dict[str, InfoSettingValue], key: str) -> int:
    value = values.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return INT_DEFAULTS[key] if key in INT_DEFAULTS else STRING_INT_DEFAULTS[key]


def setting_bool(values: dict[str, InfoSettingValue], key: str) -> bool:
    value = values.get(key)
    return value if isinstance(value, bool) else BOOL_DEFAULTS[key]


def setting_str(values: dict[str, InfoSettingValue], key: str) -> str:
    value = values.get(key)
    return value if isinstance(value, str) else STR_DEFAULTS[key]


def wb_reference(values: dict[str, InfoSettingValue]) -> datetime:
    value = values.get("wb_reference")
    return value if isinstance(value, datetime) else WB_REFERENCE_DEFAULT


def setting_position(value: InfoSettingValue) -> tuple[int, ...] | None:
    if isinstance(value, tuple):
        return value
    if isinstance(value, str):
        try:
            return tuple(int(part.strip()) for part in value.strip("()").replace(",", " ").split())
        except ValueError:
            pass
    return None
