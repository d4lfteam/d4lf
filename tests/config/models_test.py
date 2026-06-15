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
import re
from typing import Any

import pytest
from pydantic import ValidationError

from src.config.profile_models import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    GlobalUniqueModel,
    ItemFilterModel,
    ItemRarity,
    ParagonBoardModel,
    ParagonPayloadModel,
    ProfileModel,
    SigilConditionModel,
    SigilFilterModel,
    TributeFilterModel,
)
from src.config.settings_models import GeneralModel
from src.item.data.item_type import ItemType
from tests.config.data import sigils, uniques


class TestSigil:
    @staticmethod
    @pytest.mark.parametrize("data", sigils.all_bad_cases)
    def test_all_bad_cases(data: dict[str, Any]) -> None:
        data["name"] = "bad"
        with pytest.raises(ValidationError):
            ProfileModel(**data)

    @staticmethod
    @pytest.mark.parametrize("data", sigils.all_good_cases)
    def test_all_good_cases(data: dict[str, Any]) -> None:
        data["name"] = "good"
        assert ProfileModel(**data)


class TestUnique:
    @staticmethod
    @pytest.mark.parametrize(("data", "expected_msg"), uniques.all_bad_cases)
    def test_all_bad_cases(data: dict[str, Any], expected_msg: str) -> None:
        data["name"] = "bad"
        with pytest.raises(ValidationError, match=re.escape(expected_msg)):
            ProfileModel(**data)

    @staticmethod
    def test_all_good_cases() -> None:
        assert ProfileModel(**uniques.all_good_cases)


class TestGeneralProfiles:
    @staticmethod
    def test_profiles_empty_entries_are_removed() -> None:
        assert GeneralModel(profiles="alpha, , beta,   ,").profiles == ["alpha", "beta"]


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


class TestItemFilterModel:
    """Test ItemFilterModel with both naming conventions."""

    def test_min_greater_affix_in_range(self) -> None:
        """Test min_greater_affix validation for GlobalUniqueModel."""
        # Valid values 0-4
        for value in [0, 1, 2, 3, 4]:
            model = GlobalUniqueModel(min_greater_affix_count=value)
            assert model.min_greater_affix_count == value

    def test_min_greater_affix_out_of_range_fails(self) -> None:
        """Test that min_greater_affix outside [0,4] fails."""
        with pytest.raises(ValidationError, match="must be in \\[0, 4\\]"):
            GlobalUniqueModel(min_greater_affix_count=5)

    def test_item_type_parse_string(self) -> None:
        """Test item_type parsing from string."""
        model = ItemFilterModel(
            item_type="chest armor",
            affix_pool=[AffixFilterCountModel(count=[AffixFilterModel(name="critical_strike_damage")])],
        )
        assert model.item_type == [ItemType.ChestArmor]

    def test_item_type_parse_list(self) -> None:
        """Test item_type parsing from list (line 188, 17-19)."""
        # Test list input (line 19: return data)
        model = ItemFilterModel(
            item_type=["chest armor", "helm"],
            affix_pool=[AffixFilterCountModel(count=[AffixFilterModel(name="critical_strike_damage")])],
        )
        assert len(model.item_type) == 2

    def test_min_greater_affix_negative_fails(self) -> None:
        """Test that negative min_greater_affix fails (line 180-183) for GlobalUniqueModel."""
        with pytest.raises(ValidationError, match="must be in \\[0, 4\\]"):
            GlobalUniqueModel(min_greater_affix_count=-1)

    def test_camelcase_input(self) -> None:
        """Test loading with camelCase."""
        model = ItemFilterModel(
            affixPool=[], inherentPool=[], itemType=["helm"], minGreaterAffixCount=2, minPower=800, uniqueAspect=[]
        )
        assert model.affix_pool == []
        assert model.inherent_pool == []
        assert model.item_type == [ItemType.Helm]
        assert model.min_greater_affix_count == 2
        assert model.min_power == 800
        assert model.unique_aspect == []

    def test_snake_case_input(self) -> None:
        """Test loading with snake_case."""
        model = ItemFilterModel(
            affix_pool=[],
            inherent_pool=[],
            item_type=["chest armor"],
            min_greater_affix_count=3,
            min_power=900,
            unique_aspect=[],
        )
        assert model.affix_pool == []
        assert model.inherent_pool == []
        assert model.item_type == [ItemType.ChestArmor]
        assert model.min_greater_affix_count == 3
        assert model.min_power == 900
        assert model.unique_aspect == []

    def test_mixed_naming(self) -> None:
        """Test mixing both naming conventions."""
        model = ItemFilterModel(
            affixPool=[],  # camelCase
            inherent_pool=[],  # snake_case
            itemType=["gloves"],  # camelCase
            min_greater_affix_count=1,  # snake_case
            minPower=850,  # camelCase
            unique_aspect=[],  # snake_case
        )
        assert model.min_greater_affix_count == 1
        assert model.min_power == 850

    def test_export_formats(self) -> None:
        """Test both export formats."""
        model = ItemFilterModel(item_type=["boots"], min_power=825)

        snake = json.loads(model.model_dump_json(by_alias=False))
        assert "affix_pool" in snake
        assert "inherent_pool" in snake
        assert "item_type" in snake
        assert "min_greater_affix_count" in snake
        assert "min_power" in snake
        assert "unique_aspect" in snake

        camel = json.loads(model.model_dump_json(by_alias=True))
        assert "affixPool" in camel
        assert "inherentPool" in camel
        assert "itemType" in camel
        assert "minGreaterAffixCount" in camel
        assert "minPower" in camel
        assert "uniqueAspect" in camel

    def test_unique_aspect_names_must_be_unique(self) -> None:
        """Test that duplicate unique aspect names fail."""
        with pytest.raises(ValidationError, match="uniqueAspect names must be unique"):
            ItemFilterModel(
                unique_aspect=[
                    AspectUniqueFilterModel(name="ancients_oath"),
                    AspectUniqueFilterModel(name="ancients_oath"),  # duplicate
                ]
            )

    def test_unique_aspect_parse_from_dict(self) -> None:
        """Test parsing unique_aspect from dict."""
        model = ItemFilterModel(unique_aspect={"name": "ancients_oath", "min_percent_of_aspect": 80})
        assert len(model.unique_aspect) == 1
        assert model.unique_aspect[0].name == "ancients_oath"
        assert model.unique_aspect[0].min_percent_of_aspect == 80

    def test_unique_aspect_parse_empty(self) -> None:
        """Test parsing empty unique_aspect."""
        model = ItemFilterModel(unique_aspect=None)
        assert model.unique_aspect == []


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

    def test_populate_by_name_enables_both(self) -> None:
        """Test that populate_by_name=True is configured correctly."""
        # Both aliases should work independently
        model1 = ItemFilterModel(min_power=800)
        assert model1.min_power == 800

        model2 = ItemFilterModel(minPower=850)
        assert model2.min_power == 850

        # Using both would cause the last one to win (pydantic behavior with populate_by_name)
        # We just test that both are accepted

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


class TestTributeFilterModel:
    """Test TributeFilterModel with both naming conventions."""

    def test_camelcase_name(self) -> None:
        """Test tribute with camelCase name."""
        model = TributeFilterModel(name="harmony")
        assert model.name == "tribute_of_harmony"

    def test_name_with_prefix(self) -> None:
        """Test tribute with full name prefix."""
        model = TributeFilterModel(name="tribute_of_harmony")
        assert model.name == "tribute_of_harmony"

    def test_empty_name_validation(self) -> None:
        """Test empty name passes validation (line 281)."""
        # Empty name is allowed
        model = TributeFilterModel(name="")
        assert not model.name

    def test_parse_dict(self) -> None:
        """Test parsing from dict (line 224 for SigilConditionModel, 298 for TributeFilterModel)."""
        model = TributeFilterModel.model_validate({"name": "harmony"})
        assert model.name == "tribute_of_harmony"

    def test_parse_from_string_rarity(self) -> None:
        """Test parsing a rarity string (line 302)."""
        # Test with valid rarity string
        for rarity in ItemRarity:
            model = TributeFilterModel.model_validate(rarity.value)
            # Rarities are ItemRarity enum values
            assert rarity in model.rarities

    def test_parse_from_string_name(self) -> None:
        """Test parsing a tribute name string."""
        model = TributeFilterModel.model_validate("harmony")
        assert model.name == "tribute_of_harmony"

    def test_parse_from_list(self) -> None:
        """Test parsing from list (line 308)."""
        # List parses as rarities
        model = TributeFilterModel.model_validate([ItemRarity.Legendary.value, ItemRarity.Unique.value])
        assert len(model.rarities) == 2
        # Verify they are ItemRarity enums
        assert all(isinstance(r, ItemRarity) for r in model.rarities)

    def test_parse_empty_list_fails(self) -> None:
        """Test that empty list fails."""
        with pytest.raises(ValidationError, match="list cannot be empty"):
            TributeFilterModel.model_validate([])

    def test_invalid_tribute_name_fails(self) -> None:
        """Test that invalid tribute name fails."""
        with pytest.raises(ValidationError, match="No tribute named"):
            TributeFilterModel(name="invalid_tribute_123")

    def test_rarities_parse_string(self) -> None:
        """Test rarities field parsing from string (line 315)."""
        model = TributeFilterModel(rarities=ItemRarity.Legendary.value)
        # Verify it's an ItemRarity enum
        assert ItemRarity.Legendary in model.rarities

    def test_rarities_parse_list(self) -> None:
        """Test rarities field parsing from list (line 315)."""
        model = TributeFilterModel(rarities=[ItemRarity.Legendary.value])
        assert len(model.rarities) == 1
        # Verify it's an ItemRarity enum
        assert ItemRarity.Legendary in model.rarities


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


class TestProfileModel:
    """Test ProfileModel validator."""

    def test_aspect_validator_with_camelcase(self) -> None:
        """Test aspect validation with camelCase key."""
        # Valid aspect should work
        model = ProfileModel(name="test", AspectUpgrades=["accelerating"])
        assert model.aspect_upgrades == ["accelerating"]

    def test_aspect_validator_with_snake_case(self) -> None:
        """Test aspect validation with snake_case key."""
        # Valid aspect should work
        model = ProfileModel(name="test", aspect_upgrades=["accelerating"])
        assert model.aspect_upgrades == ["accelerating"]

    def test_camelcase_input(self) -> None:
        """Test loading with camelCase (legacy format)."""
        model = ProfileModel(
            name="test_profile",
            Affixes=[],
            AspectUpgrades=[],
            GlobalUniques=[GlobalUniqueModel(minPower=800)],
            Sigils={"blacklist": [], "whitelist": [], "priority": "blacklist"},
            Tributes=[],
            Paragon=None,
        )
        assert model.name == "test_profile"
        assert model.affixes == []
        assert model.aspect_upgrades == []
        assert len(model.global_uniques) == 1
        assert model.global_uniques[0].min_power == 800

    def test_snake_case_input(self) -> None:
        """Test loading with snake_case (new format)."""
        model = ProfileModel(
            name="test_profile",
            affixes=[],
            aspect_upgrades=[],
            global_uniques=[GlobalUniqueModel(min_power=900)],
            sigils={"blacklist": [], "whitelist": [], "priority": "blacklist"},
            tributes=[],
            paragon=None,
        )
        assert model.name == "test_profile"
        assert model.affixes == []
        assert model.aspect_upgrades == []
        assert len(model.global_uniques) == 1
        assert model.global_uniques[0].min_power == 900

    def test_mixed_naming(self) -> None:
        """Test mixing both naming conventions."""
        model = ProfileModel(
            name="mixed_profile",
            Affixes=[],  # camelCase
            aspect_upgrades=[],  # snake_case
            GlobalUniques=[GlobalUniqueModel(minPower=850)],  # camelCase
            sigils={"blacklist": [], "whitelist": [], "priority": "blacklist"},  # snake_case
        )
        assert model.name == "mixed_profile"
        assert model.affixes == []
        assert model.aspect_upgrades == []
        assert len(model.global_uniques) == 1

    def test_camelcase_top_level_fields(self) -> None:
        """Test that camelCase top-level fields work."""
        profile = ProfileModel(
            name="test",
            Affixes=[],
            AspectUpgrades=["accelerating"],
            GlobalUniques=[],
            Sigils={"blacklist": [], "whitelist": [], "priority": "blacklist"},
            Tributes=[],
        )
        assert profile.affixes == []
        assert profile.aspect_upgrades == ["accelerating"]
        assert profile.global_uniques == []

    def test_invalid_aspect_in_upgrades_fails(self) -> None:
        """Test that invalid aspect in AspectUpgrades fails."""
        with pytest.raises(ValidationError, match="The following aspects in AspectUpgrades do not exist"):
            ProfileModel(name="test", AspectUpgrades=["invalid_aspect_123"])

    def test_invalid_aspect_in_upgrades_snake_case_fails(self) -> None:
        """Test that invalid aspect in aspect_upgrades fails."""
        with pytest.raises(ValidationError, match="The following aspects in AspectUpgrades do not exist"):
            ProfileModel(name="test", aspect_upgrades=["invalid_aspect_123"])

    def test_aspect_upgrades_not_present(self) -> None:
        """Test that model without aspect_upgrades passes (line 336-338, 343-344)."""
        # When aspect_upgrades is not in the dict, the validator should return early
        model = ProfileModel(name="test")
        assert model.aspect_upgrades == []

    def test_export_snake_case(self) -> None:
        """Test export with by_alias=False produces snake_case."""
        model = ProfileModel(name="test", global_uniques=[GlobalUniqueModel(min_power=800)])
        exported = json.loads(model.model_dump_json(by_alias=False))

        # Check top-level fields are snake_case
        assert "affixes" in exported
        assert "aspect_upgrades" in exported
        assert "global_uniques" in exported
        assert "sigils" in exported
        assert "tributes" in exported
        assert "paragon" in exported

        # Check nested fields are also snake_case
        assert "min_power" in exported["global_uniques"][0]

        # Ensure camelCase is NOT present
        assert "Affixes" not in exported
        assert "AspectUpgrades" not in exported
        assert "GlobalUniques" not in exported
        assert "minPower" not in exported["global_uniques"][0]

    def test_export_camelcase(self) -> None:
        """Test export with by_alias=True produces camelCase."""
        model = ProfileModel(name="test", global_uniques=[GlobalUniqueModel(min_power=800)])
        exported = json.loads(model.model_dump_json(by_alias=True))

        # Check top-level fields are camelCase
        assert "Affixes" in exported
        assert "AspectUpgrades" in exported
        assert "GlobalUniques" in exported
        assert "Sigils" in exported
        assert "Tributes" in exported
        assert "Paragon" in exported

        # Check nested fields are also camelCase
        assert "minPower" in exported["GlobalUniques"][0]

        # Ensure snake_case is NOT present
        assert "affixes" not in exported
        assert "aspect_upgrades" not in exported
        assert "global_uniques" not in exported
        assert "min_power" not in exported["GlobalUniques"][0]

    def test_defaults(self) -> None:
        """Test default values work with both naming styles."""
        # Minimal profile with defaults
        model = ProfileModel(name="minimal")

        assert model.affixes == []
        assert model.aspect_upgrades == []
        assert model.global_uniques == []
        assert model.tributes == []
        assert model.paragon is None
        assert model.sigils.blacklist == []
        assert model.sigils.whitelist == []

    def test_dict_construction_camelcase(self) -> None:
        """Test constructing from dict with camelCase keys."""
        data: dict[str, Any] = {"name": "dict_test", "GlobalUniques": [{"minPower": 800}]}
        model = ProfileModel(**data)
        assert model.name == "dict_test"
        assert len(model.global_uniques) == 1
        assert model.global_uniques[0].min_power == 800

    def test_dict_construction_snake_case(self) -> None:
        """Test constructing from dict with snake_case keys."""
        data: dict[str, Any] = {"name": "dict_test", "global_uniques": [{"min_power": 900}]}
        model = ProfileModel(**data)
        assert model.name == "dict_test"
        assert len(model.global_uniques) == 1
        assert model.global_uniques[0].min_power == 900


class TestParagonModels:
    @staticmethod
    def _board_data(**overrides: object) -> dict[str, Any]:
        board = {
            "Name": "Starting Board",
            "Glyph": "glyph_name",
            "Rotation": 90,
            "Nodes": [False] * 441,
            "BoardId": "Paragon_Barb_00",
            "GlyphId": "glyph_1",
        }
        board.update(overrides)
        return board

    def test_board_accepts_supported_rotations(self) -> None:
        board = ParagonBoardModel.model_validate(self._board_data(Rotation="180°"))
        assert board.rotation == "180°"

    def test_board_rejects_unsupported_rotation(self) -> None:
        with pytest.raises(ValidationError, match="Rotation must be one of 0, 90, 180, or 270 degrees"):
            ParagonBoardModel.model_validate(self._board_data(Rotation=45))

    @pytest.mark.parametrize("rotation", [360, "360°", -90])
    def test_board_rejects_wrapped_rotation_values(self, rotation: object) -> None:
        with pytest.raises(ValidationError, match="Rotation must be one of 0, 90, 180, or 270 degrees"):
            ParagonBoardModel.model_validate(self._board_data(Rotation=rotation))

    def test_board_requires_name(self) -> None:
        with pytest.raises(ValidationError, match="Name must not be empty"):
            ParagonBoardModel.model_validate(self._board_data(Name="   "))

    def test_board_requires_nodes(self) -> None:
        board_data = self._board_data()
        board_data.pop("Nodes")

        with pytest.raises(ValidationError):
            ParagonBoardModel.model_validate(board_data)

    def test_board_requires_exactly_441_nodes(self) -> None:
        with pytest.raises(ValidationError, match="Nodes must contain exactly 441 values"):
            ParagonBoardModel.model_validate(self._board_data(Nodes=[False] * 440))

        with pytest.raises(ValidationError, match="Nodes must contain exactly 441 values"):
            ParagonBoardModel.model_validate(self._board_data(Nodes=[False] * 442))

    def test_all_false_nodes_are_valid(self) -> None:
        board = ParagonBoardModel.model_validate(self._board_data(Nodes=[False] * 441))
        assert board.nodes == [False] * 441

    def test_payload_direct_board_list_normalizes_to_one_step(self) -> None:
        payload = ParagonPayloadModel.model_validate({"Name": "Build Name", "ParagonBoardsList": [self._board_data()]})
        assert payload.paragon_boards_list == [[ParagonBoardModel.model_validate(self._board_data())]]

    def test_empty_payload_board_list_rejected(self) -> None:
        with pytest.raises(ValidationError, match="ParagonBoardsList must not be empty"):
            ParagonPayloadModel.model_validate({"Name": "Build Name", "ParagonBoardsList": []})

    def test_payload_requires_name(self) -> None:
        with pytest.raises(ValidationError):
            ParagonPayloadModel.model_validate({"ParagonBoardsList": [self._board_data()]})

    def test_payload_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            ParagonPayloadModel.model_validate({
                "Name": "Build Name",
                "ParagonBoardsList": [[self._board_data(UnknownField=True)]],
                "UnknownField": True,
            })

    def test_board_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            ParagonBoardModel.model_validate(self._board_data(UnknownField=True))

    def test_payload_accepts_board_and_glyph_ids(self) -> None:
        payload = ParagonPayloadModel.model_validate({
            "Name": "Build Name",
            "Source": "https://example.invalid",
            "GeneratedAt": "2026-06-15 00:00:00 UTC",
            "Generator": "d4lf v0.0.0",
            "ParagonBoardsList": [self._board_data()],
        })

        assert payload.paragon_boards_list[0][0].board_id == "Paragon_Barb_00"
        assert payload.paragon_boards_list[0][0].glyph_id == "glyph_1"

    def test_canonical_profile_paragon_payload_is_typed(self) -> None:
        profile = ProfileModel(name="test", Paragon={"Name": "Build Name", "ParagonBoardsList": [self._board_data()]})

        assert isinstance(profile.paragon, ParagonPayloadModel)
        assert profile.paragon.name == "Build Name"

    def test_legacy_empty_paragon_list_normalizes_to_none(self) -> None:
        profile = ProfileModel(name="test", Paragon=[])
        assert profile.paragon is None

    def test_legacy_single_payload_list_normalizes_to_one_payload(self) -> None:
        profile = ProfileModel(name="test", Paragon=[{"Name": "Build Name", "ParagonBoardsList": [self._board_data()]}])
        assert profile.paragon is not None
        assert profile.paragon.name == "Build Name"
        assert len(profile.paragon.paragon_boards_list) == 1

    def test_legacy_multi_payload_list_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Paragon must contain at most one payload"):
            ProfileModel(
                name="test",
                Paragon=[
                    {"Name": "Build One", "ParagonBoardsList": [self._board_data()]},
                    {"Name": "Build Two", "ParagonBoardsList": [self._board_data()]},
                ],
            )

    def test_profile_serialization_preserves_paragon_aliases(self) -> None:
        profile = ProfileModel(
            name="test",
            Paragon=[
                {
                    "Name": "Build Name",
                    "Source": "https://example.invalid",
                    "Generator": "d4lf v0.0.0",
                    "GeneratedAt": "2026-06-15 00:00:00 UTC",
                    "ParagonBoardsList": [self._board_data()],
                }
            ],
        )

        exported = json.loads(profile.model_dump_json(by_alias=True))
        assert exported["Paragon"]["Name"] == "Build Name"
        assert exported["Paragon"]["ParagonBoardsList"][0][0]["Name"] == "Starting Board"
        assert exported["Paragon"]["ParagonBoardsList"][0][0]["Rotation"] == "90°"
        assert len(exported["Paragon"]["ParagonBoardsList"][0][0]["Nodes"]) == 441
