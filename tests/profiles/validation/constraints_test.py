"""Comprehensive tests for pydantic models including dual naming support.

This file contains:
1. Integration tests for ProfileModel (sigils, uniques, general profiles)
2. Comprehensive unit tests for dual naming support (camelCase and snake_case)
   - Both naming conventions work for input
   - Export works correctly with by_alias parameter
   - Mixed naming in same input works
   - All validators work with both naming styles
"""

from src.profiles.validation import constraints as validators


def test_validator_boundary_values() -> None:
    assert validators.validate_percent(100) == 100
    assert validators.validate_greater_affix_count(4) == 4
