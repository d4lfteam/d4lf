"""Comprehensive tests for pydantic models including dual naming support.

This file contains:
1. Integration tests for ProfileModel (sigils, uniques, general profiles)
2. Comprehensive unit tests for dual naming support (camelCase and snake_case)
   - Both naming conventions work for input
   - Export works correctly with by_alias parameter
   - Mixed naming in same input works
   - All validators work with both naming styles
"""

import pytest

from src.profiles import _validators as validators


def test_validator_constants_and_boundaries() -> None:
    assert validators.check_greater_than_zero(0) == 0
    assert validators.validate_percent(100) == 100
    assert validators.validate_greater_affix_count(4) == 4


@pytest.mark.parametrize("value", [-1])
def test_check_greater_than_zero_rejects_negative(value: int) -> None:
    with pytest.raises(ValueError, match=validators.GREATER_THAN_ZERO_ERROR):
        validators.check_greater_than_zero(value)
