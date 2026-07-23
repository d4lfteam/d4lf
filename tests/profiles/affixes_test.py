import json

import pytest
from pydantic import ValidationError

from src.profiles import AffixFilterCountModel, AffixFilterModel, AspectUniqueFilterModel, GlobalUniqueModel


class TestAffixAspectFilterModel:
    """Test AffixAspectFilterModel parse_data validator."""

    def test_parse_from_dict(self) -> None:
        """Test parsing from dict (line 30-31)."""
        model = AffixFilterModel.model_validate({"name": "all_stats", "value": 50})
        assert model.name == "all_stats"
        assert model.value == 50

    def test_parse_from_string(self) -> None:
        """Test parsing from string."""
        model = AffixFilterModel.model_validate("all_stats")
        assert model.name == "all_stats"
        assert model.value is None

    def test_parse_from_list_single(self) -> None:
        """Test parsing from single-item list."""
        model = AffixFilterModel.model_validate(["all_stats"])
        assert model.name == "all_stats"
        assert model.value is None

    def test_parse_from_list_with_value(self) -> None:
        """Test parsing from list with value."""
        model = AffixFilterModel.model_validate(["all_stats", 50])
        assert model.name == "all_stats"
        assert model.value == 50

    def test_parse_empty_list_fails(self) -> None:
        """Test that empty list fails."""
        with pytest.raises(ValidationError, match="list, cannot be empty or larger than 2 items"):
            AffixFilterModel.model_validate([])

    def test_parse_too_long_list_fails(self) -> None:
        """Test that list with >2 items fails."""
        with pytest.raises(ValidationError, match="list, cannot be empty or larger than 2 items"):
            AffixFilterModel.model_validate(["all_stats", 50, 100])

    def test_parse_invalid_type_fails(self) -> None:
        """Test that invalid type fails (line 44-45)."""
        with pytest.raises(ValidationError, match="must be str or list"):
            AffixFilterModel.model_validate(123)  # Invalid type


class TestAffixFilterModel:
    """Test AffixFilterModel with both naming conventions."""

    def test_invalid_affix_name_fails(self) -> None:
        """Test that invalid affix name fails."""
        with pytest.raises(ValidationError, match="affix .* does not exist"):
            AffixFilterModel(name="invalid_affix_name_123")

    def test_camelcase_input(self) -> None:
        """Test loading with camelCase (legacy format)."""
        model = AffixFilterModel(name="critical_strike_damage", minPercentOfAffix=80, want_greater=True)
        assert model.min_percent_of_affix == 80
        assert model.want_greater is True

    def test_snake_case_input(self) -> None:
        """Test loading with snake_case (new format)."""
        model = AffixFilterModel(name="critical_strike_damage", min_percent_of_affix=75, want_greater=False)
        assert model.min_percent_of_affix == 75
        assert model.want_greater is False

    def test_mixed_naming(self) -> None:
        """Test mixing both naming conventions in same input."""
        model = AffixFilterModel(
            name="critical_strike_damage",
            minPercentOfAffix=60,  # camelCase
            want_greater=True,  # snake_case
        )
        assert model.min_percent_of_affix == 60
        assert model.want_greater is True

    def test_export_snake_case(self) -> None:
        """Test export with by_alias=False produces snake_case."""
        model = AffixFilterModel(name="critical_strike_damage", min_percent_of_affix=90)
        exported = json.loads(model.model_dump_json(by_alias=False))
        assert "min_percent_of_affix" in exported
        assert "minPercentOfAffix" not in exported
        assert exported["min_percent_of_affix"] == 90

    def test_export_camelcase(self) -> None:
        """Test export with by_alias=True produces camelCase."""
        model = AffixFilterModel(name="critical_strike_damage", min_percent_of_affix=85)
        exported = json.loads(model.model_dump_json(by_alias=True))
        assert "minPercentOfAffix" in exported
        assert "min_percent_of_affix" not in exported
        assert exported["minPercentOfAffix"] == 85

    def test_validator_with_camelcase(self) -> None:
        """Test validators work with camelCase input."""
        with pytest.raises(ValidationError, match="must be less than or equal to 100"):
            AffixFilterModel(name="critical_strike_damage", minPercentOfAffix=150)

    def test_validator_with_snake_case(self) -> None:
        """Test validators work with snake_case input."""
        with pytest.raises(ValidationError, match="must be less than or equal to 100"):
            AffixFilterModel(name="critical_strike_damage", min_percent_of_affix=150)

    def test_mutually_exclusive_validation_camelcase(self) -> None:
        """Test value and minPercentOfAffix are mutually exclusive (camelCase)."""
        with pytest.raises(ValidationError, match="value and minPercentOfAffix cannot both be set"):
            AffixFilterModel(name="critical_strike_damage", value=50.0, minPercentOfAffix=80)

    def test_mutually_exclusive_validation_snake_case(self) -> None:
        """Test value and min_percent_of_affix are mutually exclusive (snake_case)."""
        with pytest.raises(ValidationError, match="value and minPercentOfAffix cannot both be set"):
            AffixFilterModel(name="critical_strike_damage", value=50.0, min_percent_of_affix=80)


class TestAffixFilterCountModel:
    """Test AffixFilterCountModel with both naming conventions."""

    def test_camelcase_input(self) -> None:
        """Test loading with camelCase."""
        model = AffixFilterCountModel(
            count=[AffixFilterModel(name="critical_strike_damage", minPercentOfAffix=80)], maxCount=4, minCount=1
        )
        assert model.max_count == 4
        assert model.min_count == 1

    def test_snake_case_input(self) -> None:
        """Test loading with snake_case."""
        model = AffixFilterCountModel(
            count=[AffixFilterModel(name="critical_strike_damage", min_percent_of_affix=80)], max_count=3, min_count=2
        )
        assert model.max_count == 3
        assert model.min_count == 2

    def test_export_formats(self) -> None:
        """Test both export formats."""
        model = AffixFilterCountModel(count=[AffixFilterModel(name="critical_strike_damage")], max_count=5, min_count=1)

        # Snake case export
        snake = json.loads(model.model_dump_json(by_alias=False))
        assert "max_count" in snake
        assert "min_count" in snake

        # CamelCase export
        camel = json.loads(model.model_dump_json(by_alias=True))
        assert "maxCount" in camel
        assert "minCount" in camel


class TestAspectUniqueFilterModel:
    """Test AspectUniqueFilterModel with both naming conventions."""

    def test_invalid_aspect_name_fails(self) -> None:
        """Test that invalid aspect name fails."""
        with pytest.raises(ValidationError, match="aspect .* does not exist"):
            AspectUniqueFilterModel(name="invalid_aspect_name_123")

    def test_value_and_percent_mutually_exclusive(self) -> None:
        """Test that value and minPercentOfAspect cannot both be set."""
        with pytest.raises(ValidationError, match="value and minPercentOfAspect cannot both be set"):
            AspectUniqueFilterModel(name="ancients_oath", value=50, minPercentOfAspect=80)

    def test_camelcase_input(self) -> None:
        """Test loading with camelCase."""
        model = AspectUniqueFilterModel(
            name="ancients_oath",  # valid unique aspect name
            minPercentOfAspect=90,
        )
        assert model.min_percent_of_aspect == 90

    def test_snake_case_input(self) -> None:
        """Test loading with snake_case."""
        model = AspectUniqueFilterModel(name="ancients_oath", min_percent_of_aspect=85)
        assert model.min_percent_of_aspect == 85

    def test_export_formats(self) -> None:
        """Test both export formats."""
        model = AspectUniqueFilterModel(name="ancients_oath", min_percent_of_aspect=95)

        snake = json.loads(model.model_dump_json(by_alias=False))
        assert "min_percent_of_aspect" in snake
        assert snake["min_percent_of_aspect"] == 95

        camel = json.loads(model.model_dump_json(by_alias=True))
        assert "minPercentOfAspect" in camel
        assert camel["minPercentOfAspect"] == 95


class TestGlobalUniqueModel:
    """Test GlobalUniqueModel with both naming conventions."""

    def test_camelcase_input(self) -> None:
        """Test loading with camelCase."""
        model = GlobalUniqueModel(
            profileAlias="test_profile", minGreaterAffixCount=2, minPercentOfAspect=80, minPower=850
        )
        assert model.profile_alias == "test_profile"
        assert model.min_greater_affix_count == 2
        assert model.min_percent_of_aspect == 80
        assert model.min_power == 850

    def test_snake_case_input(self) -> None:
        """Test loading with snake_case."""
        model = GlobalUniqueModel(
            profile_alias="another_profile", min_greater_affix_count=3, min_percent_of_aspect=75, min_power=900
        )
        assert model.profile_alias == "another_profile"
        assert model.min_greater_affix_count == 3
        assert model.min_percent_of_aspect == 75
        assert model.min_power == 900

    def test_mixed_naming(self) -> None:
        """Test mixing both naming conventions."""
        model = GlobalUniqueModel(
            profileAlias="mixed",  # camelCase
            min_greater_affix_count=1,  # snake_case
            minPercentOfAspect=70,  # camelCase
            min_power=800,  # snake_case
        )
        assert model.profile_alias == "mixed"
        assert model.min_greater_affix_count == 1
        assert model.min_percent_of_aspect == 70
        assert model.min_power == 800

    def test_export_snake_case(self) -> None:
        """Test export with by_alias=False."""
        model = GlobalUniqueModel(
            profile_alias="test", min_greater_affix_count=2, min_percent_of_aspect=85, min_power=875
        )
        exported = json.loads(model.model_dump_json(by_alias=False))
        assert exported["profile_alias"] == "test"
        assert exported["min_greater_affix_count"] == 2
        assert exported["min_percent_of_aspect"] == 85
        assert exported["min_power"] == 875

    def test_export_camelcase(self) -> None:
        """Test export with by_alias=True."""
        model = GlobalUniqueModel(
            profile_alias="test", min_greater_affix_count=2, min_percent_of_aspect=85, min_power=875
        )
        exported = json.loads(model.model_dump_json(by_alias=True))
        assert exported["profileAlias"] == "test"
        assert exported["minGreaterAffixCount"] == 2
        assert exported["minPercentOfAspect"] == 85
        assert exported["minPower"] == 875

    def test_validators_camelcase(self) -> None:
        """Test validators with camelCase input."""
        # Test min_greater_affix_count > 4
        with pytest.raises(ValidationError, match="must be in \\[0, 4\\]"):
            GlobalUniqueModel(minGreaterAffixCount=5)

        # Test min_percent_of_aspect > 100
        with pytest.raises(ValidationError, match="must be less than or equal to 100"):
            GlobalUniqueModel(minPercentOfAspect=150)

    def test_validators_snake_case(self) -> None:
        """Test validators with snake_case input."""
        # Test min_greater_affix_count > 4
        with pytest.raises(ValidationError, match="must be in \\[0, 4\\]"):
            GlobalUniqueModel(min_greater_affix_count=5)

        # Test min_percent_of_aspect > 100
        with pytest.raises(ValidationError, match="must be less than or equal to 100"):
            GlobalUniqueModel(min_percent_of_aspect=150)
