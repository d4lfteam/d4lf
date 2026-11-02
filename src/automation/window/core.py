import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.automation.window import backend_noop as window_backend_noop

if TYPE_CHECKING:
    from src.automation.window.backend import WindowSpecLike

if sys.platform == "win32":
    from src.automation.window import backend_windows as _platform_backend
else:
    _platform_backend = window_backend_noop


@dataclass
class WindowSpec:
    process_name: str

    def match(self, hwnd: int, check_window_name: bool = True) -> bool:
        window_name_ok = not check_window_name or "diablo" in _platform_backend.get_window_name_from_id(hwnd).lower()
        return (
            _platform_backend.get_process_from_window_name(hwnd).casefold() == self.process_name.casefold()
            and window_name_ok
        )


def get_window_spec_id(window_spec: WindowSpecLike) -> int | None:
    return _platform_backend.get_window_spec_id(window_spec)


def start_detecting_window(window_spec: WindowSpec) -> None:
    _platform_backend.start_detecting_window(window_spec)


def detect_window(window_spec: WindowSpec) -> None:
    _platform_backend.detect_window(window_spec)


def find_and_set_window_position(window_spec: WindowSpec) -> None:
    _platform_backend.find_and_set_window_position(window_spec)


def stop_detecting_window() -> None:
    _platform_backend.stop_detecting_window()


def move_window_to_foreground(window_spec: WindowSpec) -> None:
    _platform_backend.move_window_to_foreground(window_spec)


def is_window_foreground(window_spec: WindowSpec) -> bool:
    return _platform_backend.is_window_foreground(window_spec)


def is_self_foreground() -> bool:
    return _platform_backend.is_self_foreground()


if __name__ == "__main__":
    find_and_set_window_position(WindowSpec("Diablo IV.exe"))
