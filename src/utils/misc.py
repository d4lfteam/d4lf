import ast
import math
import random
import re
import string
import time
import unicodedata
from functools import wraps
from typing import TYPE_CHECKING, TypeVar

import cv2
import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


def is_in_roi(roi: list[float], pos: tuple[float, float]):
    x, y, w, h = roi
    is_in_x_range = x < pos[0] < x + w
    is_in_y_range = y < pos[1] < y + h
    return is_in_x_range and is_in_y_range


def hms(seconds: int):
    seconds = int(seconds)
    h = seconds // 3600
    m = seconds % 3600 // 60
    s = seconds % 3600 % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def set_cv2_window(name, x, y, size):
    cv2.namedWindow(name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(name, size)
    cv2.moveWindow(name, x, y)


def generate_random_name(length_min=8, length_max=14):
    length = random.randint(length_min, length_max)
    characters = string.ascii_letters
    return "".join(random.choice(characters) for _ in range(length))


def random_number_gaussian(min_val, max_val):
    mean_iterations = (min_val + max_val) / 2
    range_span = (max_val - min_val) / 2
    std_deviation = range_span / 4
    num = random.normalvariate(mean_iterations, std_deviation)
    return max(min_val, min(max_val, num))


def random_coordinate_around_center(x, y, radius_x, radius_y):
    angle = random.uniform(0, 2 * math.pi)
    dx = random_number_gaussian(0, radius_x)
    dy = random_number_gaussian(0, radius_y)
    offset_x = int(dx * math.cos(angle))
    offset_y = int(dy * math.sin(angle))
    random_x = x + offset_x
    random_y = y + offset_y
    return np.array([random_x, random_y])


def convert_args_to_numpy(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        converted_args = []
        for arg in args:
            if isinstance(arg, list | tuple):
                converted_args.append(np.array(arg))
            else:
                converted_args.append(arg)

        converted_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, list | tuple):
                converted_kwargs[key] = np.array(value)
            else:
                converted_kwargs[key] = value

        return func(*converted_args, **converted_kwargs)

    return wrapper


def run_until_condition(
    func: Callable[[], T], is_success: Callable[[T], bool], timeout: float = 3
) -> tuple[T | None, bool]:
    """Runs the given function until the specified condition is met or the timeout is reached.

    :param func: The function to be executed repeatedly.
    :param is_success: A function that takes the result of `func` and returns True if the success condition is met.
    :param timeout: The maximum time to run the function in seconds (default 3 seconds).
    :return: A tuple containing the result of the last call to `func` and a boolean indicating if the success condition was met.
    """
    start_time = time.time()
    res = None
    success = False

    while (time.time() - start_time) < timeout:
        res = func()
        success = is_success(res)
        if success:
            break
        time.sleep(0.05)

    return res, success


def scale_vector_to_distance(vector, target_distance):
    current_distance = np.linalg.norm(vector)
    scaling_factor = 1.0 / current_distance
    normalized_vector = vector * scaling_factor
    return normalized_vector * target_distance


def slugify(value, allow_unicode=False, separator="_"):
    """Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to the desired separator. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value.lower())

    # Use the separator instead of just "-"
    value = re.sub(r"[-\s]+", separator, value)

    # Strip the separator, '-' and '_'
    strip_chars = "-_" + separator
    return value.strip(strip_chars)


def find_and_eval_math_in_string(s):
    # e.g. 615+30 Item Power -> 645 Item Power
    # Extract numbers with mathematical operators from the string
    expression = re.findall(r"(\d+[\+\-\*\/]\d+)", s)
    if expression:
        result = ast.literal_eval(expression[0])
        s = s.replace(expression[0], str(result))
    return s


def remove_commas_from_numbers(s: str) -> str:
    # Function to remove commas from matched numbers
    def repl(match):
        # Remove commas from matched string and return
        return match.group(0).replace(",", "")

    # Replace numbers with commas using the repl function
    return re.sub(r"\d{1,3}(,\d{3})*", repl, s)
