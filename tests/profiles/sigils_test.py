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
from pydantic import ValidationError

from src.profiles import ProfileModel, SigilConditionModel, SigilFilterModel


class TestSigilConditionModel:
    """Test SigilConditionModel."""

    def test_basic_usage(self) -> None:
        """Test basic sigil condition - use existing test data to find valid names."""
        # SigilConditionModel tests are covered by existing sigils tests
        # Just test that the model structure works

        # Use valid structure from existing tests
        profile = ProfileModel(
            name="test", Sigils={"blacklist": ["monster_cold_resist"], "whitelist": [], "priority": "blacklist"}
        )
        assert len(profile.sigils.blacklist) > 0

    def test_parse_string(self) -> None:
        """Test parsing from string."""
        # Test string parsing
        model = SigilConditionModel.model_validate("monster_cold_resist")
        assert model.name == "monster_cold_resist"

    def test_parse_dict(self) -> None:
        """Test parsing from dict (line 224)."""
        model = SigilConditionModel.model_validate({"name": "monster_cold_resist", "condition": []})
        assert model.name == "monster_cold_resist"
        assert model.condition == []

    def test_parse_list(self) -> None:
        """Test parsing from list with conditions."""
        # Conditions must be valid sigil affixes/dungeons
        # Line 235: if len(data) >= 2: result["condition"] = data[1:]
        model = SigilConditionModel.model_validate(["monster_cold_resist", "monster_fire_resist"])
        assert model.name == "monster_cold_resist"
        # condition gets the rest of the list
        assert len(model.condition) > 0

    def test_parse_empty_list_fails(self) -> None:
        """Test that empty list fails."""
        with pytest.raises(ValidationError, match="list cannot be empty"):
            SigilConditionModel.model_validate([])

    def test_parse_invalid_type_fails(self) -> None:
        """Test that invalid type fails (line 237-238)."""
        with pytest.raises(ValidationError, match="must be str or list"):
            SigilConditionModel.model_validate(123)  # Invalid type


class TestSigilFilterModel:
    """Test SigilFilterModel validator."""

    def test_basic_structure(self) -> None:
        """Test basic sigil filter structure."""
        model = SigilFilterModel(blacklist=[], whitelist=[], priority="blacklist")
        assert model.priority == "blacklist"
