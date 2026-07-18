from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.automation._window_backend import WindowSpecLike


def list_active_window_ids() -> list[int]:
    return []


def get_window_name_from_id(_hwnd: int) -> str:
    return ""


def get_process_from_window_name(_hwnd: int) -> str:
    return ""


def get_window_spec_id(_window_spec: WindowSpecLike) -> int | None:
    return None


def start_detecting_window(_window_spec: WindowSpecLike) -> None:
    return None


def detect_window(_window_spec: WindowSpecLike) -> None:
    return None


def find_and_set_window_position(_window_spec: WindowSpecLike) -> None:
    return None


def stop_detecting_window() -> None:
    return None


def move_window_to_foreground(_window_spec: WindowSpecLike) -> None:
    return None


def is_window_foreground(_window_spec: WindowSpecLike) -> bool:
    return False


def is_self_foreground() -> bool:
    return False
