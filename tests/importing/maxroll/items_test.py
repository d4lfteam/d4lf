import logging
from typing import TYPE_CHECKING

import pytest

from src.game_data import ItemType
from src.importing.maxroll.items import _attribute_description_corrections, _find_item_affixes
from src.item import AffixType

if TYPE_CHECKING:
    from src.type_aliases import JsonObject


def test_maxroll_item_text_correction_is_case_normalized() -> None:
    assert _attribute_description_corrections("Damage") == "damage"


def test_find_item_affixes_skips_set_count_attribute_at_info_level(caplog) -> None:
    mapping_data = {
        "affixes": {
            "HellfireTorch_Necro_05": {
                "id": 1,
                "magicType": 3,
                "attributes": [{"id": 828, "param": 2297198}],
                "desc": "+1 Set count to Rathma's Waking Touch.",
            }
        },
        "attributes": {"828": {"name": "Set_Item_Count"}},
        "skills": {},
    }

    with caplog.at_level(logging.INFO, logger="src.importing.maxroll.items"):
        affixes = _find_item_affixes(mapping_data=mapping_data, item_affixes=[{"nid": 1}], item_type=ItemType.Amulet)

    assert affixes == []
    assert any(record.levelno == logging.INFO and "Set_Item_Count" in record.message for record in caplog.records)
    assert not any(record.levelno >= logging.WARNING for record in caplog.records)


def _runeword_mapping_data(attribute_id: int, attribute_name: str, param: int) -> JsonObject:
    return {
        "affixes": {
            "Runeword_Affix": {
                "id": 1,
                "magicType": 0,
                "attributes": [{"id": attribute_id, "param": param, "value": 1}],
            },
            "X2_SkillRankBonus_Sorc_Category_Pyromancy": {
                "id": 2,
                "magicType": 0,
                "attributes": [{"id": 1158, "param": -466462940, "formula": "GearAffix_SkillRankBonus_1to2"}],
            },
        },
        "attributes": {str(attribute_id): {"name": attribute_name}},
        "uiStrings": {"damageType": {"0": "Physical"}, "resourceType": {"1": "Fury"}},
        "skills": {},
    }


@pytest.mark.parametrize(
    ("attribute_id", "attribute_name", "param", "expected"),
    [
        (-2147483367, "Bucketed_Multiplicative_Damage_Type", 0, "physical_damage_multiplier"),
        (166, "Resource_Regen_Per_Second", 1, "fury_regeneration"),
        (1158, "Skill_Rank_Skill_Tag_Bonus", -466462940, "to_pyromancy_skills"),
    ],
)
def test_find_item_affixes_maps_formulaless_runeword_affixes(
    attribute_id: int, attribute_name: str, param: int, expected: str
) -> None:
    affixes = _find_item_affixes(
        mapping_data=_runeword_mapping_data(attribute_id, attribute_name, param),
        item_affixes=[{"nid": 1, "greater": True}],
        item_type=ItemType.Mace2H,
        import_greater_affixes=True,
    )

    assert [(affix.name, affix.type) for affix in affixes] == [(expected, AffixType.greater)]


def test_find_item_affixes_maps_skill_rank_affix_with_unhandled_formula() -> None:
    mapping_data = _runeword_mapping_data(1158, "Skill_Rank_Skill_Tag_Bonus", -466462940)
    mapping_data["affixes"] = {
        "UNIQUE_SkillRankBonus_Sorc_Category_Fire": {
            "id": 1,
            "magicType": 0,
            "attributes": [{"id": 1158, "param": -466462940, "formula": "AffixIgnoreModifiers1to2"}],
        },
        "X2_SkillRankBonus_Sorc_Category_Pyromancy": {
            "id": 2,
            "magicType": 0,
            "attributes": [{"id": 1158, "param": -466462940, "formula": "GearAffix_SkillRankBonus_1to2"}],
        },
    }

    affixes = _find_item_affixes(mapping_data=mapping_data, item_affixes=[{"nid": 1}], item_type=ItemType.Amulet)

    assert [affix.name for affix in affixes] == ["to_pyromancy_skills"]


def test_find_item_affixes_skips_attribute_name_fallback_for_unknown_formula(caplog) -> None:
    mapping_data = _runeword_mapping_data(-2147483367, "Bucketed_Multiplicative_Damage_Type", 0)
    mapping_data["affixes"] = {
        "Unknown_DamageType_Physical": {
            "id": 1,
            "magicType": 0,
            "attributes": [{"id": -2147483367, "param": 0, "formula": "SomeFutureFormula"}],
        }
    }

    with caplog.at_level(logging.WARNING, logger="src.importing.maxroll.items"):
        affixes = _find_item_affixes(mapping_data=mapping_data, item_affixes=[{"nid": 1}], item_type=ItemType.Mace2H)

    assert affixes == []
    assert any("unable to map an attribute" in record.message for record in caplog.records)
