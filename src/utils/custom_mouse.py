# Mostly copied from: https://github.com/patrikoss/pyclick
import math
import random
import time

import mouse as _mouse
import numpy as np
import pytweening


def is_numeric(val):
    return isinstance(val, float | int | np.int32 | np.int64 | np.float32 | np.float64)


def is_list_of_points(value):
    def is_point(p):
        return len(p) == 2 and is_numeric(p[0]) and is_numeric(p[1])

    if not isinstance(value, list):
        return False
    try:
        return all(map(is_point, value))
    except KeyError, TypeError:
        return False


class BezierCurve:
    @staticmethod
    def binomial(n, k):
        """Returns the binomial coefficient: n choose k."""
        return math.factorial(n) / float(math.factorial(k) * math.factorial(n - k))

    @staticmethod
    def bernstein_polynomial_point(x, i, n):
        """Calculate the i-th component of a bernstein polynomial of degree n."""
        return BezierCurve.binomial(n, i) * (x**i) * ((1 - x) ** (n - i))

    @staticmethod
    def bernstein_polynomial(points):
        """Given list of control points, returns a function, which given a point [0,1] returns a point in the bezier curve described by these points."""

        def bern(t):
            n = len(points) - 1
            x = y = 0
            for i, point in enumerate(points):
                bern = BezierCurve.bernstein_polynomial_point(t, i, n)
                x += point[0] * bern
                y += point[1] * bern
            return x, y

        return bern

    @staticmethod
    def curve_points(n, points):
        """Given list of control points, returns n points in the bezier curve, described by these points."""
        curve_points = []
        bernstein_polynomial = BezierCurve.bernstein_polynomial(points)
        for i in range(n):
            t = i / (n - 1)
            curve_points += (bernstein_polynomial(t),)
        return curve_points


class HumanCurve:
    """Generates a human-like mouse curve starting at given source point, and finishing in a given destination point."""

    def __init__(self, from_point, to_point, **kwargs):
        self.from_point = from_point
        self.to_point = to_point
        self.points = self.generate_curve(**kwargs)

    def generate_curve(self, **kwargs):
        """Generates a curve according to the parameters specified below.

        You can override any of the below parameters. If no parameter is
        passed, the default value is used.
        """
        offset_boundary_x = kwargs.get("offset_boundary_x", kwargs.get("offsetBoundaryX", 100))
        offset_boundary_y = kwargs.get("offset_boundary_y", kwargs.get("offsetBoundaryY", 100))
        left_boundary = (
            kwargs.get("left_boundary", kwargs.get("leftBoundary", min(self.from_point[0], self.to_point[0])))
            - offset_boundary_x
        )
        right_boundary = (
            kwargs.get("right_boundary", kwargs.get("rightBoundary", max(self.from_point[0], self.to_point[0])))
            + offset_boundary_x
        )
        down_boundary = (
            kwargs.get("down_boundary", kwargs.get("downBoundary", min(self.from_point[1], self.to_point[1])))
            - offset_boundary_y
        )
        up_boundary = (
            kwargs.get("up_boundary", kwargs.get("upBoundary", max(self.from_point[1], self.to_point[1])))
            + offset_boundary_y
        )
        knots_count = kwargs.get("knots_count", kwargs.get("knotsCount", 2))
        distortion_mean = kwargs.get("distortion_mean", kwargs.get("distortionMean", 1))
        distortion_stdev = kwargs.get("distortion_stdev", kwargs.get("distortionStdev", 1))
        distortion_frequency = kwargs.get("distortion_frequency", kwargs.get("distortionFrequency", 0.4))
        tween = kwargs.get("tweening", pytweening.easeOutQuad)
        target_points = kwargs.get("target_points", kwargs.get("targetPoints", 10))

        internal_knots = self.generate_internal_knots(
            left_boundary, right_boundary, down_boundary, up_boundary, knots_count
        )
        points = self.generate_points(internal_knots)
        points = self.distort_points(points, distortion_mean, distortion_stdev, distortion_frequency)
        return self.tween_points(points, tween, target_points)

    def generate_internal_knots(self, left_boundary, right_boundary, down_boundary, up_boundary, knots_count):
        """Generates the internal knots used during generation of bezier curvePoints.

        or any interpolation function. The points are taken at random from
        a surface delimited by given boundaries.
        Exactly knotsCount internal knots are randomly generated.
        """
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
        return list(zip(knots_x, knots_y, strict=False))

    def generate_points(self, knots):
        """Generates bezier curve points on a curve, according to the internal knots passed as parameter."""
        if not is_list_of_points(knots):
            msg = "knots must be valid list of points"
            raise ValueError(msg)

        mid_pts_cnt = max(abs(self.from_point[0] - self.to_point[0]), abs(self.from_point[1] - self.to_point[1]), 2)
        knots = [self.from_point, *knots, self.to_point]
        return BezierCurve.curve_points(mid_pts_cnt, knots)

    def distort_points(self, points, distortion_mean, distortion_stdev, distortion_frequency):
        """Distorts the curve described by (x,y) points, so that the curve is not ideally smooth.

        Distortion happens by randomly, according to normal distribution,
        adding an offset to some of the points.
        """
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

    def tween_points(self, points, tween, target_points):
        """Chooses a number of points(targetPoints) from the list(points) according to tweening function(tween).

        This function in fact controls the velocity of mouse movement
        """
        if not is_list_of_points(points):
            msg = "points must be valid list of points"
            raise ValueError(msg)
        if not isinstance(target_points, int) or target_points < 2:
            msg = "targetPoints must be an integer greater or equal to 2"
            raise ValueError(msg)

        # tween is a function that takes a float 0..1 and returns a float 0..1
        res = []
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
    ):
        from_point = _mouse.get_position()
        dist = math.dist((x, y), from_point)
        offset_boundary_x = max(10, int(0.08 * dist))
        offset_boundary_y = max(10, int(0.08 * dist))
        target_points = min(6, max(3, int(0.004 * dist)))
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
            _mouse.move(point[0], point[1], duration=delta)
        time.sleep(0.05)

    @staticmethod
    def _is_clicking_safe():
        return True

    @staticmethod
    def click(button):
        if button != "left" or Mouse._is_clicking_safe():
            _mouse.click(button)

    @staticmethod
    def get_position():
        return _mouse.get_position()
