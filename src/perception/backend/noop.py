from typing import TYPE_CHECKING, Never

if TYPE_CHECKING:
    import logging
    import queue
    from collections.abc import Callable


class NoopTTSBackend:
    def create_pipe(self, _logger: logging.Logger) -> Never:
        message = "TTS named pipes are only supported on Windows."
        raise RuntimeError(message)

    def read_pipe(
        self,
        _create_pipe: Callable[[], int],
        _data_queue: queue.Queue[str],
        _logger: logging.Logger,
        _set_connected: Callable[[bool], None],
    ) -> None:
        return

    def start_connection(
        self, _start_find_item: Callable[[], None], _start_read_pipe: Callable[[], None], _logger: logging.Logger
    ) -> None:
        return
