from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class NoopTTSBackend:
    def create_pipe(self, _logger):
        message = "TTS named pipes are only supported on Windows."
        raise RuntimeError(message)

    def read_pipe(self, _create_pipe, _data_queue, _logger, _set_connected: Callable[[bool], None]) -> None:
        return

    def start_connection(self, _start_find_item, _start_read_pipe, _logger) -> None:
        return
