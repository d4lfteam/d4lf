import sys
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable

if sys.platform == "win32":
    from .windows import WindowsTTSBackend

    _Backend = WindowsTTSBackend
else:
    from .noop import NoopTTSBackend

    _Backend = NoopTTSBackend


class TTSBackend(Protocol):
    def create_pipe(self, logger) -> object: ...

    def read_pipe(
        self, create_pipe: Callable[[], object], data_queue, logger, set_connected: Callable[[bool], None]
    ) -> None: ...

    def start_connection(
        self, start_find_item: Callable[[], None], start_read_pipe: Callable[[], None], logger
    ) -> None: ...


def load_backend() -> TTSBackend:
    return _Backend()
