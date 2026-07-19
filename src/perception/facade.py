from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

from src.perception import listener as _listener
from src.perception.parser.item import parse_item_text

if TYPE_CHECKING:
    import numpy as np

    from src.perception.matching.models import SearchResult, TemplateReferences

Publisher = _listener.Publisher
filter_data = _listener.filter_data
find_item_start = _listener.find_item_start
fix_data = _listener.fix_data


def read_latest_item():
    return parse_item_text(list(_listener.LAST_ITEM))


def latest_item_lines() -> list[str]:
    return list(_listener.LAST_ITEM)


def is_connected() -> bool:
    return _listener.CONNECTED


def start_connection() -> None:
    _listener.start_connection()


class TemplateQuery(Protocol):
    ref: TemplateReferences
    mode: str

    def detect(self, img: np.ndarray | None = None) -> SearchResult: ...

    def is_visible(self, img: np.ndarray | None = None) -> bool: ...


def capture(force_new: bool = False):
    from src.perception.capture.core import Cam  # ruff:ignore[import-outside-top-level]

    return Cam().grab(force_new=force_new)


def game_window_ready() -> bool:
    from src.perception.capture.core import Cam  # ruff:ignore[import-outside-top-level]

    return Cam().is_offset_set()


def game_window_roi() -> dict[str, int]:
    from src.perception.capture.core import Cam  # ruff:ignore[import-outside-top-level]

    return cast("dict[str, int]", dict(Cam().window_roi))


def monitor_to_window(coordinate):
    from src.perception.capture.core import Cam  # ruff:ignore[import-outside-top-level]

    return Cam().monitor_to_window(coordinate)


def window_to_monitor(coordinate):
    from src.perception.capture.core import Cam  # ruff:ignore[import-outside-top-level]

    return Cam().window_to_monitor(coordinate)


def abs_window_to_monitor(coordinate):
    from src.perception.capture.core import Cam  # ruff:ignore[import-outside-top-level]

    return Cam().abs_window_to_monitor(coordinate)


def update_window_position(offset_x: int, offset_y: int, width: int, height: int) -> None:
    from src.perception.capture.core import Cam  # ruff:ignore[import-outside-top-level]

    Cam().update_window_pos(offset_x, offset_y, width, height)


def reset_window_position() -> None:
    from src.perception.capture.core import Cam  # ruff:ignore[import-outside-top-level]

    Cam().reset_window_position()


def create_template_query(**kwargs) -> TemplateQuery:
    from src.perception.matching.models import SearchArgs  # ruff:ignore[import-outside-top-level]

    return SearchArgs(**kwargs)


def search_templates(*args, **kwargs):
    from src.perception.matching.engine import search  # ruff:ignore[import-outside-top-level]

    return search(*args, **kwargs)


def crop_image(image, roi):
    from src.perception.image import crop  # ruff:ignore[import-outside-top-level]

    return crop(image, roi)


def alpha_mask(image):
    from src.perception.image import alpha_to_mask  # ruff:ignore[import-outside-top-level]

    return alpha_to_mask(image)


def compare_image_histograms(image_a, image_b):
    from src.perception.image import compare_histograms  # ruff:ignore[import-outside-top-level]

    return compare_histograms(image_a, image_b)


def center_of_roi(roi):
    from src.perception.roi import get_center  # ruff:ignore[import-outside-top-level]

    return get_center(roi)


def grid_rois(roi, rows: int, columns: int):
    from src.perception.roi import to_grid  # ruff:ignore[import-outside-top-level]

    return to_grid(roi, rows, columns)
