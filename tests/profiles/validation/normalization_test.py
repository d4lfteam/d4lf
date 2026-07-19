"""Comprehensive tests for pydantic models including dual naming support.

This file contains:
1. Integration tests for ProfileModel (sigils, uniques, general profiles)
2. Comprehensive unit tests for dual naming support (camelCase and snake_case)
   - Both naming conventions work for input
   - Export works correctly with by_alias parameter
   - Mixed naming in same input works
   - All validators work with both naming styles
"""

import json

from src.profiles import GlobalUniqueModel, ItemFilterModel


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_string_fields(self) -> None:
        """Test empty string fields work correctly."""
        model = GlobalUniqueModel(profile_alias="")
        assert not model.profile_alias

        exported_snake = json.loads(model.model_dump_json(by_alias=False))
        assert not exported_snake["profile_alias"]

        exported_camel = json.loads(model.model_dump_json(by_alias=True))
        assert not exported_camel["profileAlias"]

    def test_zero_values(self) -> None:
        """Test zero values are handled correctly."""
        model = GlobalUniqueModel(min_greater_affix_count=0, min_percent_of_aspect=0, min_power=0)
        assert model.min_greater_affix_count == 0
        assert model.min_percent_of_aspect == 0
        assert model.min_power == 0

    def test_boundary_values(self) -> None:
        """Test boundary values."""
        # Maximum valid values
        model = GlobalUniqueModel(
            min_greater_affix_count=4,  # max is 4
            min_percent_of_aspect=100,  # max is 100
            min_power=1,  # must be > 0
        )
        assert model.min_greater_affix_count == 4
        assert model.min_percent_of_aspect == 100
        assert model.min_power == 1

    def test_validate_by_name_and_alias_enable_both(self) -> None:
        """Test that both field names and aliases are accepted."""
        # Both aliases should work independently
        model1 = ItemFilterModel(min_power=800)
        assert model1.min_power == 800

        model2 = ItemFilterModel(minPower=850)
        assert model2.min_power == 850

        # Field names and aliases remain independently accepted for construction.

    def test_field_order_independence(self) -> None:
        """Test that field order doesn't matter with mixed naming."""
        model1 = GlobalUniqueModel(
            min_power=800,  # snake_case first
            minGreaterAffixCount=2,  # camelCase second
        )
        model2 = GlobalUniqueModel(
            minGreaterAffixCount=2,  # camelCase first
            min_power=800,  # snake_case second
        )
        assert model1.min_power == model2.min_power
        assert model1.min_greater_affix_count == model2.min_greater_affix_count
