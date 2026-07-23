import datetime
from typing import TypeVar

from PyQt6.QtCore import QSettings

type InfoSettingValue = int | str | bool | tuple[int, ...] | datetime.datetime | None
T = TypeVar("T", int, str, bool)
U = TypeVar("U")


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

    result: dict[str, InfoSettingValue] = {
        "x": value("x", 100, int),
        "y": value("y", 100, int),
        "font_size": value("font_size", 14, int),
        "font_family": value("font_family", "Consolas", str),
        "orientation": value("orientation", "horizontal", str),
        "next_boss_name": value("next_boss_name", "Unknown", str),
        "show_wb": flag("show_wb", default=True),
        "show_legion": flag("show_legion", default=True),
        "show_ht": flag("show_ht", default=True),
        "show_gold": flag("show_gold", default=True),
        "show_gph": flag("show_gph", default=True),
        "show_total_gold": flag("show_total_gold", default=True),
        "show_exp": flag("show_exp", default=True),
        "show_eph": flag("show_eph", default=True),
        "show_total_exp": flag("show_total_exp", default=True),
        "show_t2l": flag("show_t2l", default=True),
        "show_next_scan": flag("show_next_scan", default=True),
        "locked": flag("locked", default=False),
        "capture_gold_stats": flag("capture_gold_stats", default=False),
        "capture_exp_stats": flag("capture_exp_stats", default=False),
        "check_exp_on_inventory_open": flag("check_exp_on_inventory_open", default=True),
        "exp_age_before_refresh": integer("exp_age_before_refresh", 5),
        "exp_bar_pos": position("exp_bar_pos"),
        "session_total_gold": integer("session_total_gold", 0),
        "session_total_exp": integer("session_total_exp", 0),
    }
    raw_reference = store.value("wb_reference", "2024-01-01 00:00:00", type=str)
    try:
        result["wb_reference"] = datetime.datetime.strptime(raw_reference, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=datetime.UTC
        )
    except TypeError, ValueError:
        result["wb_reference"] = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
    return result


def save_settings(values: dict[str, InfoSettingValue]) -> None:
    store = QSettings("d4lf", "InfoOverlay")
    for key, raw_value in values.items():
        value = raw_value
        if key == "wb_reference" and isinstance(raw_value, datetime.datetime):
            value = raw_value.strftime("%Y-%m-%d %H:%M:%S")
        elif key == "exp_bar_pos":
            value = str(value) if value is not None else "None"
        store.setValue(key, value)


def setting_int(values: dict[str, InfoSettingValue], key: str, default: int) -> int:
    value = values.get(key)
    return value if isinstance(value, int) else default


def setting_bool(values: dict[str, InfoSettingValue], key: str, default: bool) -> bool:
    value = values.get(key)
    return value if isinstance(value, bool) else default


def setting_str(values: dict[str, InfoSettingValue], key: str, default: str) -> str:
    value = values.get(key)
    return value if isinstance(value, str) else default


def setting_datetime(values: dict[str, InfoSettingValue], key: str, default: datetime.datetime) -> datetime.datetime:
    value = values.get(key)
    return value if isinstance(value, datetime.datetime) else default


def setting_position(value: InfoSettingValue) -> tuple[int, ...] | None:
    if isinstance(value, tuple):
        return value
    if isinstance(value, str):
        try:
            return tuple(int(part.strip()) for part in value.strip("()").replace(",", " ").split())
        except ValueError:
            pass
    return None
