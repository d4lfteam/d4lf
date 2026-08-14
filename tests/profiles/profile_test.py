import json
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from src.game_data import ItemRarity
from src.profiles import (
    DynamicCharmFilterModel,
    DynamicSealFilterModel,
    GlobalUniqueModel,
    ProfileModel,
    TributeFilterModel,
)

if TYPE_CHECKING:
    from src.type_aliases import JsonValue

"""Comprehensive tests for pydantic models including dual naming support.

This file contains:
1. Integration tests for ProfileModel (sigils, uniques, general profiles)
2. Comprehensive unit tests for dual naming support (camelCase and snake_case)
   - Both naming conventions work for input
   - Export works correctly with by_alias parameter
   - Mixed naming in same input works
   - All validators work with both naming styles
"""


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
            Tributes={},
            Seals=[{"Cooldown": {"affixPool": [{"count": ["cooldown_reduction"]}], "rarities": ["legendary"]}}],
            Charms=[{"Life": {"affixPool": [{"count": ["maximum_life"]}], "rarities": ["rare"]}}],
            Paragon=None,
        )
        assert model.name == "test_profile"
        assert model.affixes == []
        assert model.aspect_upgrades == []
        assert len(model.global_uniques) == 1
        assert model.global_uniques[0].min_power == 800
        assert model.seals[0].root["Cooldown"].rarities == [ItemRarity.Legendary]
        assert model.charms[0].root["Life"].rarities == [ItemRarity.Rare]

    def test_snake_case_input(self) -> None:
        """Test loading with snake_case (new format)."""
        model = ProfileModel(
            name="test_profile",
            affixes=[],
            aspect_upgrades=[],
            global_uniques=[GlobalUniqueModel(min_power=900)],
            sigils={"blacklist": [], "whitelist": [], "priority": "blacklist"},
            tributes={},
            seals=[{"Cooldown": {"affix_pool": [{"count": ["cooldown_reduction"]}]}}],
            charms=[{"Life": {"affix_pool": [{"count": ["maximum_life"]}]}}],
            paragon=None,
        )
        assert model.name == "test_profile"
        assert model.affixes == []
        assert model.aspect_upgrades == []
        assert len(model.global_uniques) == 1
        assert model.global_uniques[0].min_power == 900
        assert isinstance(model.seals[0], DynamicSealFilterModel)
        assert isinstance(model.charms[0], DynamicCharmFilterModel)
        assert model.seals[0].root["Cooldown"].affix_pool[0].count[0].name == "cooldown_reduction"
        assert model.charms[0].root["Life"].affix_pool[0].count[0].name == "maximum_life"

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

    def test_tributes_list_shape_is_migrated_to_single_object(self) -> None:
        model = ProfileModel.model_validate({
            "name": "tributes_profile",
            "Tributes": [{"name": ["harmony"]}, {"rarity": ["legendary"]}],
        })
        assert isinstance(model.tributes, TributeFilterModel)
        assert model.tributes.name == ["tribute_of_harmony"]
        assert model.tributes.rarities == [ItemRarity.Legendary]

    @pytest.mark.parametrize(
        "tributes",
        [
            [{"name": 123}],
            [{"rarity": [123]}],
            [{"raritty": "legendary"}],
            [{"rarity": "rare", "rarities": "unique"}],
            [123],
        ],
    )
    def test_invalid_legacy_tribute_entries_are_rejected(self, tributes: list[JsonValue]) -> None:
        with pytest.raises(ValidationError):
            ProfileModel.model_validate({"name": "invalid_tributes", "Tributes": tributes})

    def test_camelcase_top_level_fields(self) -> None:
        """Test that camelCase top-level fields work."""
        profile = ProfileModel(
            name="test",
            Affixes=[],
            AspectUpgrades=["accelerating"],
            GlobalUniques=[],
            Sigils={"blacklist": [], "whitelist": [], "priority": "blacklist"},
            Tributes={},
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
        assert "seals" in exported
        assert "charms" in exported
        assert "sigils" in exported
        assert "tributes" in exported
        assert "paragon" in exported

        # Check nested fields are also snake_case
        assert "min_power" in exported["global_uniques"][0]

        # Ensure camelCase is NOT present
        assert "Affixes" not in exported
        assert "AspectUpgrades" not in exported
        assert "GlobalUniques" not in exported
        assert "Seals" not in exported
        assert "Charms" not in exported
        assert "minPower" not in exported["global_uniques"][0]

    def test_export_camelcase(self) -> None:
        """Test export with by_alias=True produces camelCase."""
        model = ProfileModel(name="test", global_uniques=[GlobalUniqueModel(min_power=800)])
        exported = json.loads(model.model_dump_json(by_alias=True))

        # Check top-level fields are camelCase
        assert "Affixes" in exported
        assert "AspectUpgrades" in exported
        assert "GlobalUniques" in exported
        assert "Seals" in exported
        assert "Charms" in exported
        assert "Sigils" in exported
        assert "Tributes" in exported
        assert "Paragon" in exported

        # Check nested fields are also camelCase
        assert "minPower" in exported["GlobalUniques"][0]

        # Ensure snake_case is NOT present
        assert "affixes" not in exported
        assert "aspect_upgrades" not in exported
        assert "global_uniques" not in exported
        assert "seals" not in exported
        assert "charms" not in exported
        assert "min_power" not in exported["GlobalUniques"][0]

    def test_defaults(self) -> None:
        """Test default values work with both naming styles."""
        # Minimal profile with defaults
        model = ProfileModel(name="minimal")

        assert model.affixes == []
        assert model.aspect_upgrades == []
        assert model.global_uniques == []
        assert model.seals == []
        assert model.charms == []
        assert model.tributes is None
        assert model.paragon is None
        assert model.sigils.blacklist == []
        assert model.sigils.whitelist == []

    def test_dict_construction_camelcase(self) -> None:
        """Test constructing from dict with camelCase keys."""
        data: dict[str, JsonValue] = {"name": "dict_test", "GlobalUniques": [{"minPower": 800}]}
        model = ProfileModel.model_validate(data)
        assert model.name == "dict_test"
        assert len(model.global_uniques) == 1
        assert model.global_uniques[0].min_power == 800

    def test_dict_construction_snake_case(self) -> None:
        """Test constructing from dict with snake_case keys."""
        data: dict[str, JsonValue] = {"name": "dict_test", "global_uniques": [{"min_power": 900}]}
        model = ProfileModel.model_validate(data)
        assert model.name == "dict_test"
        assert len(model.global_uniques) == 1
        assert model.global_uniques[0].min_power == 900
