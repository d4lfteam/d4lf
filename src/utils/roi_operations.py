import logging
from enum import Enum

from src.config.ui import ResManager

LOGGER = logging.getLogger(__name__)


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


def intersect(*rects: list[tuple[int, int, int, int]] | tuple[int, int, int, int]) -> tuple[int, int, int, int] | None:
    """Finds the intersection of multiple rectangles.

    :param rects: The rectangles to intersect. Each rectangle is represented as a tuple of four integers (x_min, y_min, width, height).
    :return: The intersection of all rectangles, represented as (x_min, y_min, width, height), or None if there is no intersection.
    """
    if len(rects) == 1 and isinstance(rects[0], list):
        rects = rects[0]

    max_x_min = max(rect[0] for rect in rects)
    max_y_min = max(rect[1] for rect in rects)
    min_x_max = min(rect[0] + rect[2] for rect in rects)
    min_y_max = min(rect[1] + rect[3] for rect in rects)

    if max_x_min < min_x_max and max_y_min < min_y_max:
        return max_x_min, max_y_min, min_x_max - max_x_min, min_y_max - max_y_min
    # LOGGER.debug(f"No intersection between {rects}.")
    return None


def bounding_box(
    *args: list[tuple[int, int, int, int]] | tuple[int, int, int, int] | list[tuple[int, int]] | tuple[int, int],
) -> tuple[int, int, int, int] | None:
    """Finds the bounding rectangle of a set of rectangles or coordinates.

    :param args: The rectangles or coordinates to bound.
        Each rectangle is represented as a tuple of four integers (x_min, y_min, width, height).
        Each coordinate is represented as a tuple of two integers (x, y).
    :return: The smallest rectangle that contains all the input rectangles or coordinates, represented as (x_min, y_min, width, height).
    """
    if len(args) == 1 and isinstance(args[0], list):
        args = args[0]

    min_x, min_y, max_x, max_y = (float("inf"), float("inf"), float("-inf"), float("-inf"))

    for arg in args:
        if len(arg) == 2:  # if it's a coordinate
            x, y = arg
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
        elif len(arg) == 4:  # if it's a rectangle
            x, y, w, h = arg
            min_x, max_x = min(min_x, x), max(max_x, x + w)
            min_y, max_y = min(min_y, y), max(max_y, y + h)
        else:
            LOGGER.error(
                f"Invalid argument: {arg}. Each argument should be either a coordinate (2 integers) or a rectangle (4 integers)."
            )
            return None

    return min_x, min_y, max_x - min_x, max_y - min_y


def to_grid(roi: tuple[int, int, int, int], rows: int, columns: int) -> set[tuple[int, int, int, int]]:
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

    rectangles = []
    for i in range(rows):
        for j in range(columns):
            cell_width = base_cell_width + (1 if j < extra_width else 0)
            cell_height = base_cell_height + (1 if i < extra_height else 0)
            cell_x_min = x_min + sum(base_cell_width + (1 if k < extra_width else 0) for k in range(j))
            cell_y_min = y_min + sum(base_cell_height + (1 if k < extra_height else 0) for k in range(i))
            rectangles.append((cell_x_min, cell_y_min, cell_width, cell_height))

    rectangles.sort(key=lambda x: (x[1], x[0]))  # sort row major
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
