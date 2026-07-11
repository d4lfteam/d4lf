from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import logging
    from collections.abc import Callable


def create_pipe(_logger: logging.Logger):
    msg = "TTS named pipes are only supported on Windows."
    raise RuntimeError(msg)


def read_pipe(
    _create_pipe_fn: Callable[[], object], _data_queue, _logger: logging.Logger, _set_connected: Callable[[bool], None]
) -> None:
    return


def start_connection(
    _start_find_item: Callable[[], None], _start_read_pipe: Callable[[], None], _logger: logging.Logger
) -> None:
    return
