import queue
from typing import Any, cast

from src.loot.highlighting import VisionModeWithHighlighting


def test_highlighting_mode_queues_clear_and_match_requests():
    wrapped = cast("Any", VisionModeWithHighlighting)
    mode_type = next(cell.cell_contents for cell in wrapped.__closure__ if isinstance(cell.cell_contents, type))
    mode = object.__new__(mode_type)
    mode.queue = queue.Queue()

    mode.request_clear()
    mode.request_match_box("item", (1, 2, 3, 4), "result", "markers")

    assert mode.queue.get_nowait() == ("clear",)
    assert mode.queue.get_nowait() == ("match", "item", (1, 2, 3, 4), "result", "markers")
