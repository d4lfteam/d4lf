import logging
import operator
from collections.abc import Iterable
from enum import Enum
from numbers import Integral

from src.config.ui import ResManager

LOGGER = logging.getLogger(__name__)

type Rectangle = tuple[int, int, int, int]


def compare_tuples(t1, t2, uncertainty):
    return abs(t1[0] - t2[0]) <= uncertainty and abs(t1[1] - t2[1]) <= uncertainty


def create_roi_from_rel(point, rel_roi):
    if isinstance(rel_roi, str):
        rel_roi = getattr(ResManager().roi, rel_roi)
    x, y = point
    rel_x, rel_y, w, h = rel_roi
    abs_x = x + rel_x
    abs_y = y + rel_y
    return abs_x, abs_y, w, h


def fit_roi_to_window_size(roi, size):
    ww, wh = size
    x, y, w, h = roi

    success = True

    # Check if the ROI is entirely out of bounds
    if x >= ww or y >= wh:
        return False, None

    # Adjust the width and height to fit within the window
    if x + w > ww:
        w = ww - x
    if y + h > wh:
        h = wh - y

    # Check if ROI is valid after adjustments
    if w <= 0 or h <= 0:
        return False, None

    updated_roi = (x, y, w, h)
    return success, updated_roi


def get_center(roi: tuple[int, int, int, int]) -> tuple[int, int]:
    """Finds the center of a region of interest.

    :param roi: Region of interest in the format (x, y, w, h).
    :return: Coordinates of the center.
    """
    x, y, w, h = roi
    return round(x + w / 2), round(y + h / 2)


def _as_values(value: object) -> tuple[object, ...] | None:
    if not isinstance(value, Iterable):
        return None
    try:
        return tuple(value)
    except TypeError:
        return None


def _as_rectangle(value: object) -> Rectangle | None:
    values = _as_values(value)
    if values is None:
        return None
    if len(values) != 4 or not all(isinstance(item, Integral) for item in values):
        return None
    x, y, width, height = values
    if (
        not isinstance(x, Integral)
        or not isinstance(y, Integral)
        or not isinstance(width, Integral)
        or not isinstance(height, Integral)
    ):
        return None
    return int(x), int(y), int(width), int(height)


def intersect(*rects: Iterable[object]) -> Rectangle | None:
    """Finds the intersection of multiple rectangles.

    :param rects: The rectangles to intersect. Each rectangle is represented as a tuple of four integers (x_min, y_min, width, height).
    :return: The intersection of all rectangles, represented as (x_min, y_min, width, height), or None if there is no intersection.
    """
    normalized_rects: list[Rectangle] = []
    for rect in rects:
        rect_values = _as_values(rect)
        if rect_values is None:
            return None
        if direct_rect := _as_rectangle(rect_values):
            normalized_rects.append(direct_rect)
            continue
        for nested_rect in rect_values:
            normalized_rect = _as_rectangle(nested_rect)
            if normalized_rect is None:
                return None
            normalized_rects.append(normalized_rect)

    if not normalized_rects:
        return None
    max_x_min = max(rect[0] for rect in normalized_rects)
    max_y_min = max(rect[1] for rect in normalized_rects)
    min_x_max = min(rect[0] + rect[2] for rect in normalized_rects)
    min_y_max = min(rect[1] + rect[3] for rect in normalized_rects)

    if max_x_min < min_x_max and max_y_min < min_y_max:
        return max_x_min, max_y_min, min_x_max - max_x_min, min_y_max - max_y_min
    # LOGGER.debug(f"No intersection between {rects}.")
    return None


def bounding_box(*args: Iterable[object]) -> Rectangle | None:
    """Finds the bounding rectangle of a set of rectangles or coordinates.

    :param args: The rectangles or coordinates to bound.
        Each rectangle is represented as a tuple of four integers (x_min, y_min, width, height).
        Each coordinate is represented as a tuple of two integers (x, y).
    :return: The smallest rectangle that contains all the input rectangles or coordinates, represented as (x_min, y_min, width, height).
    """
    if len(args) == 1 and isinstance(args[0], Iterable):
        materialized_arg = _as_values(args[0])
        if materialized_arg is None:
            return None
        if _as_rectangle(materialized_arg) is not None or (
            len(materialized_arg) == 2 and all(isinstance(value, Integral) for value in materialized_arg)
        ):
            normalized_args = [materialized_arg]
        else:
            normalized_args = list(materialized_arg)
    else:
        normalized_args = list(args)

    min_x: int | None = None
    min_y: int | None = None
    max_x: int | None = None
    max_y: int | None = None

    for arg in normalized_args:
        values = _as_values(arg)
        if values is None:
            return None
        if len(values) == 2 and all(isinstance(value, Integral) for value in values):  # if it's a coordinate
            x_value, y_value = values
            if not isinstance(x_value, Integral) or not isinstance(y_value, Integral):
                return None
            x, y = int(x_value), int(y_value)
            min_x = x if min_x is None else min(min_x, x)
            max_x = x if max_x is None else max(max_x, x)
            min_y = y if min_y is None else min(min_y, y)
            max_y = y if max_y is None else max(max_y, y)
        elif len(values) == 4 and all(isinstance(value, Integral) for value in values):  # if it's a rectangle
            x_value: object = values[0]
            y_value: object = values[1]
            w_value: object = values[2]
            h_value: object = values[3]
            if (
                not isinstance(x_value, Integral)
                or not isinstance(y_value, Integral)
                or not isinstance(w_value, Integral)
                or not isinstance(h_value, Integral)
            ):
                return None
            x, y, w, h = int(x_value), int(y_value), int(w_value), int(h_value)
            max_x_value, max_y_value = x + w, y + h
            min_x = x if min_x is None else min(min_x, x)
            max_x = max_x_value if max_x is None else max(max_x, max_x_value)
            min_y = y if min_y is None else min(min_y, y)
            max_y = max_y_value if max_y is None else max(max_y, max_y_value)
        else:
            LOGGER.error(
                f"Invalid argument: {arg}. Each argument should be either a coordinate (2 integers) or a rectangle (4 integers)."
            )
            return None

    if min_x is None or min_y is None or max_x is None or max_y is None:
        return None
    return min_x, min_y, max_x - min_x, max_y - min_y


def to_grid(roi: Rectangle, rows: int, columns: int) -> list[Rectangle]:
    """Splits a rectangle of interest (ROI) into a grid of smaller rectangles.

    :param roi: The rectangle to split, represented as (x_min, y_min, width, height).
    :param rows: The number of rows in the grid.
    :param columns: The number of columns in the grid.
    :return: A set of rectangles representing the grid. Each rectangle is represented as (x_min, y_min, width, height).
    """
    x_min, y_min, width, height = roi
    base_cell_width = width // columns
    base_cell_height = height // rows

    extra_width = width % columns
    extra_height = height % rows

    rectangles: list[Rectangle] = []
    for i in range(rows):
        for j in range(columns):
            cell_width = base_cell_width + (1 if j < extra_width else 0)
            cell_height = base_cell_height + (1 if i < extra_height else 0)
            cell_x_min = x_min + sum(base_cell_width + (1 if k < extra_width else 0) for k in range(j))
            cell_y_min = y_min + sum(base_cell_height + (1 if k < extra_height else 0) for k in range(i))
            rectangles.append((cell_x_min, cell_y_min, cell_width, cell_height))

    rectangles.sort(key=operator.itemgetter(1, 0))  # sort row major
    return rectangles


class Condition(Enum):
    WITHIN = "within"
    ALIGN_Y = "align_y"
    ALIGN_X = "align_x"


def is_in_roi(
    coor: tuple[int, int], roi: tuple[int, int, int, int], condition: Condition | str = Condition.WITHIN
) -> bool:
    """Checks the position of a given coordinate relative to a given rectangle of interest (ROI).

    :param coor: The coordinate to check, represented as (x, y).
    :param roi: The rectangle to check against, represented as (x_min, y_min, width, height).
    :param condition: The condition to check for:
                      - Condition.WITHIN: Check if coordinate is inside the ROI.
                      - Condition.ALIGN_Y: Check if coordinate aligns with ROI in y-direction.
                      - Condition.ALIGN_X: Check if coordinate aligns with ROI in x-direction.
    :return: True if the coordinate meets the specified condition relative to the ROI, False otherwise.
    """
    x, y = coor
    x_min, y_min, width, height = roi
    x_max = x_min + width
    y_max = y_min + height

    # Convert string condition to Enum value if necessary
    if isinstance(condition, str):
        condition = Condition(condition)

    if condition == Condition.WITHIN:
        return x_min <= x <= x_max and y_min <= y <= y_max
    if condition == Condition.ALIGN_Y:
        return x_min <= x <= x_max and not (y_min <= y <= y_max)
    if condition == Condition.ALIGN_X:
        return not (x_min <= x <= x_max) and y_min <= y <= y_max
    msg = "Invalid condition specified"
    raise ValueError(msg)
