import sys
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import logging
    import queue
    from collections.abc import Callable

if sys.platform == "win32":
    from .windows import WindowsTTSBackend

    _Backend = WindowsTTSBackend
else:
    from .noop import NoopTTSBackend

    _Backend = NoopTTSBackend


class TTSBackend(Protocol):
    def create_pipe(self, logger: logging.Logger) -> int: ...

    def read_pipe(
        self,
        create_pipe: Callable[[], int],
        data_queue: queue.Queue[str],
        logger: logging.Logger,
        set_connected: Callable[[bool], None],
    ) -> None: ...

    def start_connection(
        self, start_find_item: Callable[[], None], start_read_pipe: Callable[[], None], logger: logging.Logger
    ) -> None: ...


def load_backend() -> TTSBackend:
    return _Backend()
