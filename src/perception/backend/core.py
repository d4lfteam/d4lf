from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable


class TTSBackend(Protocol):
    def create_pipe(self, logger) -> object: ...

    def read_pipe(
        self, create_pipe: Callable[[], object], data_queue, logger, set_connected: Callable[[bool], None]
    ) -> None: ...

    def start_connection(
        self, start_find_item: Callable[[], None], start_read_pipe: Callable[[], None], logger
    ) -> None: ...


def load_backend() -> TTSBackend:
    if __import__("sys").platform == "win32":
        from src.perception.backend.windows import WindowsTTSBackend  # ruff:ignore[import-outside-top-level]

        return WindowsTTSBackend()
    from src.perception.backend.noop import NoopTTSBackend  # ruff:ignore[import-outside-top-level]

    return NoopTTSBackend()
