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

import pytest
from pydantic import ValidationError

from src.game_data import ItemRarity, ItemType
from src.profiles import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    CharmFilterModel,
    GlobalUniqueModel,
    ItemFilterModel,
    SealFilterModel,
    TributeFilterModel,
)


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
        model = ItemFilterModel.model_validate({"unique_aspect": None})
        assert model.unique_aspect == []

    def test_affix_pool_rejects_charm_only_affix(self) -> None:
        affix_name = "bonus_kill_experience"

        with pytest.raises(ValidationError, match=f"affixPool affix {affix_name} does not exist"):
            ItemFilterModel(affix_pool=[AffixFilterCountModel(count=[AffixFilterModel(name=affix_name)])])

    def test_inherent_pool_rejects_seal_only_affix(self) -> None:
        affix_name = "adept_action_damage_reduction_while_moving"

        with pytest.raises(ValidationError, match=f"inherentPool affix {affix_name} does not exist"):
            ItemFilterModel(inherent_pool=[AffixFilterCountModel(count=[AffixFilterModel(name=affix_name)])])


class TestTributeFilterModel:
    def test_name_single_value_normalizes_to_list(self) -> None:
        model = TributeFilterModel.model_validate({"name": "harmony"})
        assert model.name == ["tribute_of_harmony"]

    def test_name_list_normalizes_entries(self) -> None:
        model = TributeFilterModel.model_validate({"name": ["harmony", "tribute_of_andariel"]})
        assert model.name == ["tribute_of_harmony", "tribute_of_andariel"]

    def test_rarity_alias_loads(self) -> None:
        model = TributeFilterModel.model_validate({"rarity": ["legendary"]})
        assert model.rarities == [ItemRarity.Legendary]

    def test_legacy_rarities_alias_still_loads(self) -> None:
        model = TributeFilterModel.model_validate({"rarities": ["legendary"]})
        assert model.rarities == [ItemRarity.Legendary]

    def test_serialization_alias_uses_rarity(self) -> None:
        model = TributeFilterModel.model_validate({"rarity": ["legendary"]})
        dumped = model.model_dump(by_alias=True)
        assert "rarity" in dumped
        assert "rarities" not in dumped

    def test_invalid_tribute_name_fails(self) -> None:
        with pytest.raises(ValidationError, match="No tribute named"):
            TributeFilterModel(name=["invalid_tribute_123"])

    def test_default_is_empty_lists(self) -> None:
        model = TributeFilterModel()
        assert model.name == []
        assert model.rarities == []


class TestCharmFilterModel:
    def test_extra_fields_are_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            CharmFilterModel.model_validate({"unexpected": True})

    def test_set_name_is_validated_and_normalized(self) -> None:
        model = CharmFilterModel(set=["Breath of the Frozen Sea"])
        assert model.set == ["breath_of_the_frozen_sea"]

    def test_invalid_set_fails(self) -> None:
        with pytest.raises(ValidationError, match="set invalid_set does not exist"):
            CharmFilterModel(set=["invalid set"])

    def test_unique_aspect_is_normalized(self) -> None:
        model = CharmFilterModel(uniqueAspect=[AspectUniqueFilterModel(name="Fractured Winterglass")])
        assert model.unique_aspect == [AspectUniqueFilterModel(name="fractured_winterglass")]

    def test_duplicate_unique_aspects_fail(self) -> None:
        with pytest.raises(ValidationError, match="uniqueAspect names must be unique"):
            CharmFilterModel(
                uniqueAspect=[
                    AspectUniqueFilterModel(name="tuskhelm_of_joritz_the_mighty"),
                    AspectUniqueFilterModel(name="Tuskhelm of Joritz the Mighty"),
                ]
            )

    def test_duplicate_sets_fail(self) -> None:
        with pytest.raises(ValidationError, match="set names must be unique"):
            CharmFilterModel(set=["Sescherons Fury", "sescherons_fury"])

    def test_set_and_unique_aspect_are_mutually_exclusive(self) -> None:
        with pytest.raises(ValidationError, match="can't define both set and unique aspect"):
            CharmFilterModel(
                set=["Sescherons Fury"], uniqueAspect=[AspectUniqueFilterModel(name="tuskhelm_of_joritz_the_mighty")]
            )

    def test_affix_pool_accepts_charm_only_affix(self) -> None:
        affix_name = "bonus_kill_experience"
        model = CharmFilterModel(affix_pool=[AffixFilterCountModel(count=[AffixFilterModel(name=affix_name)])])
        assert model.affix_pool[0].count[0].name == affix_name

    def test_affix_pool_rejects_seal_only_affix(self) -> None:
        affix_name = "adept_action_damage_reduction_while_moving"
        with pytest.raises(ValidationError, match=f"affixPool affix {affix_name} does not exist"):
            CharmFilterModel(affix_pool=[AffixFilterCountModel(count=[AffixFilterModel(name=affix_name)])])


class TestSealFilterModel:
    def test_affix_pool_accepts_seal_only_affix(self) -> None:
        affix_name = "adept_action_damage_reduction_while_moving"
        model = SealFilterModel(affix_pool=[AffixFilterCountModel(count=[AffixFilterModel(name=affix_name)])])
        assert model.affix_pool[0].count[0].name == affix_name

    def test_affix_pool_rejects_charm_only_affix(self) -> None:
        affix_name = "bonus_kill_experience"
        with pytest.raises(ValidationError, match=f"affixPool affix {affix_name} does not exist"):
            SealFilterModel(affix_pool=[AffixFilterCountModel(count=[AffixFilterModel(name=affix_name)])])
