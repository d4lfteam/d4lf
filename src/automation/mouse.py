import ctypes
import math
import random
import sys
import time
from typing import TYPE_CHECKING, TypeGuard, cast

import numpy as np
import pytweening
from pynput.mouse import Button, Controller

if TYPE_CHECKING:
    from collections.abc import Callable

from src.type_aliases import JsonValue, Numeric, Point

_MOUSE = Controller()

_BUTTONS: dict[str, Button] = {"left": Button.left, "right": Button.right, "middle": Button.middle}

# SendInput-based absolute mouse move so Diablo 4's DirectInput/Raw Input pipeline
# detects the cursor travel (SetCursorPos alone is not seen by the game).
if sys.platform == "win32":
    from ctypes import wintypes

    _MOUSEEVENTF_MOVE = 0x0001
    _MOUSEEVENTF_ABSOLUTE = 0x8000

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class _INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("mi", _MOUSEINPUT)]

    def _move_mouse_abs(x: int, y: int) -> None:
        screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        screen_h = ctypes.windll.user32.GetSystemMetrics(1)
        inp = _INPUT()
        inp.type = 0  # INPUT_MOUSE
        inp.mi.dx = int(x * 65535 / screen_w)
        inp.mi.dy = int(y * 65535 / screen_h)
        inp.mi.mouseData = 0
        inp.mi.dwFlags = _MOUSEEVENTF_MOVE | _MOUSEEVENTF_ABSOLUTE
        inp.mi.time = 0
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))

else:

    def _move_mouse_abs(x: int, y: int) -> None:
        _MOUSE.position = (x, y)


type PointComponent = Numeric | np.integer | np.floating
type PointCandidate = tuple[PointComponent, PointComponent] | list[PointComponent]
type PointInput = list[PointCandidate] | JsonValue
type CurveOption = Numeric | Callable[[float], float]


def is_numeric(val: PointComponent | str | bool | None) -> bool:
    return isinstance(val, (float, int, np.integer, np.floating))


def is_list_of_points(value: PointInput) -> TypeGuard[list[Point]]:
    def is_point(p: PointCandidate) -> bool:
        return len(p) == 2 and is_numeric(p[0]) and is_numeric(p[1])

    if not isinstance(value, list):
        return False
    try:
        return all(map(is_point, cast("list[PointCandidate]", value)))
    except KeyError, TypeError:
        return False


class BezierCurve:
    @staticmethod
    def binomial(n: int, k: int) -> float:
        """Returns the binomial coefficient: n choose k."""
        return math.factorial(n) / float(math.factorial(k) * math.factorial(n - k))

    @staticmethod
    def bernstein_polynomial_point(x: float, i: int, n: int) -> float:
        """Calculate the i-th component of a bernstein polynomial of degree n."""
        return float(BezierCurve.binomial(n, i) * (x**i) * ((1 - x) ** (n - i)))

    @staticmethod
    def bernstein_polynomial(points: list[tuple[float, float]]) -> Callable[[float], tuple[float, float]]:
        """Given list of control points, returns a function, which given a point [0,1] returns a point in the bezier curve described by these points."""

        def bern(t: float) -> tuple[float, float]:
            n = len(points) - 1
            x = y = 0
            for i, point in enumerate(points):
                bern = BezierCurve.bernstein_polynomial_point(t, i, n)
                x += point[0] * bern
                y += point[1] * bern
            return (x, y)

        return bern

    @staticmethod
    def curve_points(n: int, points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """Given list of control points, returns n points in the bezier curve, described by these points."""
        curve_points: list[tuple[float, float]] = []
        bernstein_polynomial = BezierCurve.bernstein_polynomial(points)
        for i in range(n):
            t = i / (n - 1)
            curve_points += (bernstein_polynomial(t),)
        return curve_points


class HumanCurve:
    """Generates a human-like mouse curve starting at given source point, and finishing in a given destination point."""

    def __init__(self, from_point: Point, to_point: Point, **kwargs: CurveOption) -> None:
        self.from_point = from_point
        self.to_point = to_point
        self.points = self.generate_curve(**kwargs)

    def generate_curve(self, **kwargs: CurveOption) -> list[Point]:
        offset_boundary_x = cast("int", kwargs.get("offset_boundary_x", kwargs.get("offsetBoundaryX", 100)))
        offset_boundary_y = cast("int", kwargs.get("offset_boundary_y", kwargs.get("offsetBoundaryY", 100)))
        left_boundary = (
            cast(
                "int",
                kwargs.get("left_boundary", kwargs.get("leftBoundary", min(self.from_point[0], self.to_point[0]))),
            )
            - offset_boundary_x
        )
        right_boundary = (
            cast(
                "int",
                kwargs.get("right_boundary", kwargs.get("rightBoundary", max(self.from_point[0], self.to_point[0]))),
            )
            + offset_boundary_x
        )
        down_boundary = (
            cast(
                "int",
                kwargs.get("down_boundary", kwargs.get("downBoundary", min(self.from_point[1], self.to_point[1]))),
            )
            - offset_boundary_y
        )
        up_boundary = (
            cast("int", kwargs.get("up_boundary", kwargs.get("upBoundary", max(self.from_point[1], self.to_point[1]))))
            + offset_boundary_y
        )
        knots_count = cast("int", kwargs.get("knots_count", kwargs.get("knotsCount", 2)))
        distortion_mean = cast("float", kwargs.get("distortion_mean", kwargs.get("distortionMean", 1)))
        distortion_stdev = cast("float", kwargs.get("distortion_stdev", kwargs.get("distortionStdev", 1)))
        distortion_frequency = cast("float", kwargs.get("distortion_frequency", kwargs.get("distortionFrequency", 0.4)))
        tween = cast("Callable[[float], float]", kwargs.get("tweening", pytweening.easeOutQuad))
        target_points = cast("int", kwargs.get("target_points", kwargs.get("targetPoints", 10)))

        internal_knots = self.generate_internal_knots(
            left_boundary, right_boundary, down_boundary, up_boundary, knots_count
        )
        points = self.generate_points(internal_knots)
        points = self.distort_points(points, distortion_mean, distortion_stdev, distortion_frequency)
        return self.tween_points(points, tween, target_points)

    def generate_internal_knots(
        self, left_boundary: int, right_boundary: int, down_boundary: int, up_boundary: int, knots_count: int
    ) -> list[Point]:
        """Generates random internal knots for the Bezier curve within the supplied boundaries."""
        if not (
            is_numeric(left_boundary)
            and is_numeric(right_boundary)
            and is_numeric(down_boundary)
            and is_numeric(up_boundary)
        ):
            msg = "Boundaries must be numeric"
            raise ValueError(msg)
        if not isinstance(knots_count, int) or knots_count < 0:
            msg = "knotsCount must be non-negative integer"
            raise ValueError(msg)
        if left_boundary > right_boundary:
            msg = "leftBoundary must be less than or equal to rightBoundary"
            raise ValueError(msg)
        if down_boundary > up_boundary:
            msg = "downBoundary must be less than or equal to upBoundary"
            raise ValueError(msg)

        knots_x = np.random.choice(range(left_boundary, right_boundary), size=knots_count)
        knots_y = np.random.choice(range(down_boundary, up_boundary), size=knots_count)
        return [(float(x), float(y)) for x, y in zip(knots_x, knots_y, strict=False)]

    def generate_points(self, knots: list[Point]) -> list[Point]:
        """Generates bezier curve points on a curve, according to the internal knots passed as parameter."""
        if not is_list_of_points(knots):
            msg = "knots must be valid list of points"
            raise ValueError(msg)

        mid_pts_cnt = int(
            max(abs(self.from_point[0] - self.to_point[0]), abs(self.from_point[1] - self.to_point[1]), 2)
        )
        knots = [self.from_point, *knots, self.to_point]
        return BezierCurve.curve_points(mid_pts_cnt, knots)

    def distort_points(
        self, points: list[Point], distortion_mean: float, distortion_stdev: float, distortion_frequency: float
    ) -> list[Point]:
        """Distorts curve points by randomly adding normally distributed offsets."""
        if not (is_numeric(distortion_mean) and is_numeric(distortion_stdev) and is_numeric(distortion_frequency)):
            msg = "Distortions must be numeric"
            raise ValueError(msg)
        if not is_list_of_points(points):
            msg = "points must be valid list of points"
            raise ValueError(msg)
        if not (0 <= distortion_frequency <= 1):
            msg = "distortionFrequency must be in range [0,1]"
            raise ValueError(msg)

        distorted = []
        for i in range(1, len(points) - 1):
            x, y = points[i]
            delta = np.random.normal(distortion_mean, distortion_stdev) if random.random() < distortion_frequency else 0
            distorted += ((x, y + delta),)
        return [points[0], *distorted, points[-1]]

    def tween_points(self, points: list[Point], tween: Callable[[float], float], target_points: int) -> list[Point]:
        """Chooses target_points from points according to the tweening function."""
        if not is_list_of_points(points):
            msg = "points must be valid list of points"
            raise ValueError(msg)
        if not isinstance(target_points, int) or target_points < 2:
            msg = "targetPoints must be an integer greater or equal to 2"
            raise ValueError(msg)

        res: list[tuple[float, float]] = []
        for i in range(target_points):
            index = int(tween(float(i) / (target_points - 1)) * (len(points) - 1))
            res += (points[index],)
        return res


class Mouse:
    @staticmethod
    def move(
        x: int,
        y: int,
        absolute: bool = True,
        randomize: int | tuple[int, int] = 5,
        delay_factor: tuple[float, float] = (0.2, 0.3),
    ) -> None:
        from_point = Mouse.get_position()
        if not absolute:
            x = from_point[0] + x
            y = from_point[1] + y

        if isinstance(randomize, int):
            randomize = int(randomize)
            if randomize > 0:
                x = int(x) + random.randrange(-randomize, +randomize)
                y = int(y) + random.randrange(-randomize, +randomize)
        else:
            randomize = (int(randomize[0]), int(randomize[1]))
            if randomize[1] > 0 and randomize[0] > 0:
                x = int(x) + random.randrange(-randomize[0], +randomize[0])
                y = int(y) + random.randrange(-randomize[1], +randomize[1])

        dist = math.dist((x, y), from_point)
        offset_boundary_x = max(10, int(0.08 * dist))
        offset_boundary_y = max(10, int(0.08 * dist))
        target_points = min(80, max(12, int(0.05 * dist)))
        human_curve = HumanCurve(
            from_point,
            (x, y),
            offset_boundary_x=offset_boundary_x,
            offset_boundary_y=offset_boundary_y,
            target_points=target_points,
        )

        duration = min(0.3, max(0.05, dist * 0.0004) * random.uniform(delay_factor[0], delay_factor[1]))
        delta = duration / len(human_curve.points)

        for point in human_curve.points:
            _move_mouse_abs(int(point[0]), int(point[1]))
            time.sleep(delta)
        time.sleep(0.05)

    @staticmethod
    def _is_clicking_safe() -> bool:
        return True

    @staticmethod
    def click(button: str) -> None:
        if button != "left" or Mouse._is_clicking_safe():
            _MOUSE.click(_BUTTONS[button])

    @staticmethod
    def get_position() -> tuple[int, int]:
        return int(_MOUSE.position[0]), int(_MOUSE.position[1])
