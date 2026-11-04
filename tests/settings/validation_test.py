import pytest

from src.settings.validation import check_greater_than_zero


def test_check_greater_than_zero_accepts_zero() -> None:
    assert check_greater_than_zero(0) == 0


def test_check_greater_than_zero_rejects_negative() -> None:
    with pytest.raises(ValueError, match="must be greater than zero"):
        check_greater_than_zero(-1)
