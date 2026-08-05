import queue
from typing import Protocol

from src.loot.highlighting import VisionModeWithHighlighting


class _HighlightingMode(Protocol):
    queue: queue.Queue[object]

    def request_clear(self) -> None: ...

    def request_match_box(
        self, item: object, item_roi: tuple[int, int, int, int], result: object, markers: object
    ) -> None: ...


def _new_highlighting_mode() -> _HighlightingMode:
    closure = getattr(VisionModeWithHighlighting, "__closure__", None)
    if not isinstance(closure, tuple):
        raise AssertionError
    for cell in closure:
        implementation = cell.cell_contents
        if isinstance(implementation, type):
            implementation_type: type[_HighlightingMode] = implementation
            return object.__new__(implementation_type)
    raise AssertionError


def test_highlighting_mode_queues_clear_and_match_requests():
    mode = _new_highlighting_mode()
    mode.queue = queue.Queue()

    mode.request_clear()
    mode.request_match_box("item", (1, 2, 3, 4), "result", "markers")

    assert mode.queue.get_nowait() == ("clear",)
    assert mode.queue.get_nowait() == ("match", "item", (1, 2, 3, 4), "result", "markers")
