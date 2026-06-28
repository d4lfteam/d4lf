import sys
import threading

if sys.platform != "darwin":
    import keyboard


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


def validate_greater_affix_count(v: int) -> int:
    if not 0 <= v <= 4:
        msg = "must be in [0, 4]"
        raise ValueError(msg)
    return v


def validate_hotkey(k: str) -> str:
    keyboard.parse_hotkey(k)
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
