import sys
import threading

if sys.platform != "darwin":
    import keyboard


def _drop_negative_scan_codes(scan_codes: tuple[int, ...]) -> tuple[int, ...]:
    positive_scan_codes = tuple(scan_code for scan_code in scan_codes if scan_code > 0)
    return positive_scan_codes or scan_codes


def to_keyboard_hotkey(hotkey: str) -> tuple[tuple[tuple[int, ...], ...], ...] | str:
    if not hotkey:
        return hotkey

    return tuple(
        tuple(_drop_negative_scan_codes(scan_codes) for scan_codes in step) for step in keyboard.parse_hotkey(hotkey)
    )


def check_greater_than_zero(v: int) -> int:
    if v < 0:
        msg = "must be greater than zero"
        raise ValueError(msg)
    return v


def validate_percent(v: int) -> int:
    check_greater_than_zero(v)
    if v > 100:
        msg = "must be less than or equal to 100"
        raise ValueError(msg)
    return v


def validate_hotkey(k: str, *, allow_empty: bool = False) -> str:
    if not k:
        if allow_empty:
            return k
        keyboard.parse_hotkey(k)
        return k
    keyboard.parse_hotkey(to_keyboard_hotkey(k))
    return k


def singleton(cls):
    instances = {}
    lock = threading.Lock()

    def get_instance(*args, **kwargs):
        with lock:
            if cls not in instances:
                instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


def str_to_int_list(s: str) -> list[int]:
    if not s:
        return []
    return [int(x) for x in s.split(",")]
