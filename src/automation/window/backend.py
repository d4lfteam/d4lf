from typing import Protocol


class WindowSpecLike(Protocol):
    process_name: str

    def match(self, hwnd: int, check_window_name: bool = True) -> bool: ...
