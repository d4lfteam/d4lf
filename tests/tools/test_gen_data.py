from src.tools.gen_data import _build_affix_description, _find_affix_parameter


def test_affix_parameter_prefers_power_name_over_file_name():
    parameter = _find_affix_parameter(
        affix_name="Tempered_Damage_Necro_Skill_BoneSpirit_Tier1",
        attribute={"__eAttribute_name__": "Power_Damage_Percent_Bonus", "nParam": 469641},
        power_names={469641: "Bone Spirit"},
        skill_tag_names={},
        affix_tokens={"damage": [], "resource": [], "resistance": []},
    )

    assert parameter == "Bone Spirit"


def test_build_affix_description_uses_power_name_for_value_parameter():
    affix_data = {
        "ptItemAffixAttributes": [
            {"tAttribute": {"__eAttribute_name__": "Power_Damage_Percent_Bonus", "nParam": 469641}}
        ]
    }

    description = _build_affix_description(
        affix_name="Tempered_Damage_Necro_Skill_BoneSpirit_Tier1",
        affix_data=affix_data,
        attribute_descriptions={"Power_Damage_Percent_Bonus": "+[{VALUE2}*100|1%|] {VALUE1} Damage"},
        power_names={469641: "Bone Spirit"},
        skill_tag_names={},
        affix_tokens={"damage": [], "resource": [], "resistance": []},
    )

    assert description == "bone spirit damage"


def test_build_affix_description_uses_damage_to_status_token():
    affix_data = {
        "ptItemAffixAttributes": [
            {"tAttribute": {"__eAttribute_name__": "Damage_Percent_Bonus_Vs_CC_Target", "nParam": 1}}
        ]
    }

    description = _build_affix_description(
        affix_name="Damage_to_Immobilized",
        affix_data=affix_data,
        attribute_descriptions={"Damage_Percent_Bonus_Vs_CC_Target": "+[{VALUE2}*100|1%|] Damage to {VALUE1} Enemies"},
        power_names={},
        skill_tag_names={},
        affix_tokens={"damage": [], "resource": [], "resistance": []},
    )

    assert description == "damage to immobilized enemies"
