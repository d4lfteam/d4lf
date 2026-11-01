from src.settings.binding import validate_hotkey as validate_hotkey_binding

MAX_PERCENT = 100
MAX_GREATER_AFFIX_COUNT = 4


def check_greater_than_zero(v: int) -> int:
    if v < 0:
        msg = "must be greater than zero"
        raise ValueError(msg)
    return v


def validate_percent(v: int) -> int:
    check_greater_than_zero(v)
    if v > MAX_PERCENT:
        msg = "must be less than or equal to 100"
        raise ValueError(msg)
    return v


def validate_greater_affix_count(v: int) -> int:
    if not 0 <= v <= MAX_GREATER_AFFIX_COUNT:
        msg = "must be in [0, 4]"
        raise ValueError(msg)
    return v


def validate_hotkey(k: str) -> str:
    return validate_hotkey_binding(k)


def str_to_int_list(s: str) -> list[int]:
    if not s:
        return []
    return [int(x) for x in s.split(",")]
