import numpy as np

from src.automation._mouse import is_numeric


def test_is_numeric_accepts_python_and_numpy_numbers() -> None:
    assert is_numeric(1)
    assert is_numeric(1.0)
    assert is_numeric(np.int64(1))
    assert is_numeric(np.float64(1.0))


def test_is_numeric_rejects_non_numeric_values() -> None:
    assert not is_numeric("1")
