def list_active_window_ids() -> list[int]:
    return []


def get_window_name_from_id(_hwnd: int) -> str:
    return ""


def get_process_from_window_name(_hwnd: int) -> str:
    return ""


def get_window_spec_id(_window_spec) -> int | None:
    return None


def start_detecting_window(_window_spec):
    return


def detect_window(_window_spec):
    return


def find_and_set_window_position(_window_spec):
    return


def stop_detecting_window():
    return


def move_window_to_foreground(_window_spec):
    return


def is_window_foreground(_window_spec) -> bool:
    return False


def is_self_foreground() -> bool:
    return False
