import numpy as np

from src.automation.mouse import BezierCurve, is_list_of_points, is_numeric


def test_mouse_geometry_helpers_validate_points_and_endpoints() -> None:
    assert is_numeric(3)
    assert is_list_of_points([(0, 0), (1.5, 2)])
    assert not is_list_of_points([(0, "x")])
    assert BezierCurve.curve_points(2, [(0, 0), (10, 10)]) == [(0.0, 0.0), (10.0, 10.0)]


def test_is_numeric_accepts_numpy_numbers_and_rejects_strings() -> None:
    assert is_numeric(np.int64(1))
    assert is_numeric(np.float64(1.0))
    assert not is_numeric("1")
