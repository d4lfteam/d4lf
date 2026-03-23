"""New config loading and verification using pydantic. For now, both will exist in parallel hence _new."""

import sys
import threading

if sys.platform != "darwin":
    try:
        import keyboard
    except Exception:  # pragma: no cover
        keyboard = None  # type: ignore[assignment]
else:
    keyboard = None  # type: ignore[assignment]


def check_greater_than_zero(v: int) -> int:
    if v < 0:
        msg = "must be greater than zero"
        raise ValueError(msg)
    return v


def validate_hotkey(k: str) -> str:
    if keyboard is None:
        return k
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
