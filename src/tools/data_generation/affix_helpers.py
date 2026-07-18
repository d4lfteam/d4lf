"""Affix placeholder and localization helpers."""

import re
from typing import TYPE_CHECKING

from src.tools.data_generation.common import AffixGenerationContext, get_first_gbid_name, get_power_id, string_list_map
from src.tools.data_generation.constants import (
    CROWD_CONTROL_LOCALISATION_IDS,
    CROWD_CONTROL_TYPES,
    CROWD_CONTROLLED_LOCALISATION_IDS,
    CROWD_CONTROLLED_TYPES,
    DAMAGE_LOCALISATION_IDS,
    DAMAGE_TYPES,
    DOT_LOCALISATION_IDS,
    DOT_TYPES,
    LOCALISATION_ID_RENAMES,
    NECRO_PET_LOCALISATION_IDS,
    NECRO_PET_NAMES,
    POWER_LOCALISATION_IDS,
    POWER_SUB_LOCALISATION_IDS,
    RESISTANCE_TYPES,
    RESOURCE_LOCALISATION_IDS,
    RESOURCE_TYPES,
    SHAPESHIFT_FORMS,
    SKILL_TAG_LOCALISATION_IDS,
    SKILL_TAG_SUB_LOCALISATION_IDS,
    WEAPON_TYPE_LOCALISATION_IDS,
)

if TYPE_CHECKING:
    from pathlib import Path


def update_affix_localisation_id(
    localisation_id: str,
    parameter: int,
    attribute_descriptions: dict[str, str],
    attribute_prefixes: set[str],
    power_by_sno: dict[int, str],
    skill_tags_by_sno: dict[int, list[str]],
    weapon_types_by_sno: dict[int, str],
) -> str:
    if localisation_id not in attribute_prefixes:
        return LOCALISATION_ID_RENAMES.get(localisation_id, localisation_id)

    sub_id = ""
    if localisation_id in POWER_SUB_LOCALISATION_IDS:
        sub_id = get_power_id(power_by_sno, parameter)
    elif localisation_id in SKILL_TAG_SUB_LOCALISATION_IDS:
        sub_id = get_first_gbid_name(skill_tags_by_sno, parameter)
    elif localisation_id == "Primary_Resource_Gain_Bonus_Percent_Per_Weapon_Requirement":
        sub_id = weapon_types_by_sno.get(parameter, "")
    elif localisation_id == "Resistance":
        sub_id = RESISTANCE_TYPES.get(parameter, "")
    elif localisation_id in {
        "Damage_Percent_Bonus_Against_Dot_Type",
        "Damage_Percent_Reduction_From_Dotted_Enemy",
        "DOT_DPS_Bonus_Percent_Per_Damage_Type",
    }:
        sub_id = {0: "Physical", 1: "Fire", 4: "Poison", 5: "Shadow"}.get(parameter, "")
    else:
        print(f"WARNING: Sub localisation data available but rules not set for {localisation_id}.")

    sub_localisation_id = f"{localisation_id}#{sub_id}" if sub_id else ""
    if sub_localisation_id and sub_localisation_id in attribute_descriptions:
        localisation_id = sub_localisation_id

    return LOCALISATION_ID_RENAMES.get(localisation_id, localisation_id)


def replace_numeric_value_placeholders(description: str) -> str:
    description = re.sub(r"\[([^%]+?)\]", "#", description)
    description = re.sub(r"\[(.+?)\]", "#%", description)
    description = description.replace("+{VALUE1}", "+#")
    description = description.replace("{VALUE2}", "#")
    description = description.replace("+{VALUE2}", "+#")
    description = description.replace("+{vALUE2}", "+#")
    description = description.replace("{s1}", "#")
    description = description.replace("{s2}", "#")
    description = description.replace("{icon:bullet}", "")
    description = description.replace("{c_important}", "")
    description = description.replace("{c_label}", "")
    description = description.replace("{c_legendary}", "")
    description = description.replace("{c_number}", "")
    description = description.replace("{c:FFf74444}", "")
    description = description.replace("{/c}", "")
    description = description.replace("{d}", " ")
    description = description.replace("{u}", "")
    description = description.replace("{/u}", "")
    description = description.replace("{i}", "")
    description = description.replace("{/i}", "")
    return description.replace("|2", "")


def replace_from_label_map(description: str, label_map: dict[str, str], label: str) -> str:
    value = label_map.get(label, "")
    return description.replace("{VALUE1}", value) if value else description


def replace_power_placeholder(
    description: str, parameter: int, d4data_dir: Path, language: str, power_by_sno: dict[int, str]
) -> str:
    if "{" not in description and "}" not in description:
        return description

    power_id = get_power_id(power_by_sno, parameter)
    if not power_id:
        return description

    power_string_file = d4data_dir / f"json/{language}_Text/meta/StringList/Power_{power_id}.stl.json"
    if not power_string_file.exists():
        print(f"WARNING: Could not find file named {power_string_file} in d4data.")
        return description

    skill_name = string_list_map(power_string_file).get("name", "")
    if not skill_name:
        return description
    return description.replace("{VALUE1}", skill_name).replace("{vALUE1}", skill_name)


def replace_parameter_placeholder(
    description: str,
    localisation_id: str,
    parameter: int,
    context: AffixGenerationContext,
    d4data_dir: Path,
    language: str,
) -> str:
    base_id = localisation_id.split("#", maxsplit=1)[0]
    if base_id in POWER_LOCALISATION_IDS:
        return replace_power_placeholder(description, parameter, d4data_dir, language, context["power_by_sno"])
    if base_id in SKILL_TAG_LOCALISATION_IDS:
        skill_category = get_first_gbid_name(context["skill_tags_by_sno"], parameter)
        return replace_from_label_map(description, context["skill_tags"], f"{skill_category}_TagName")
    if base_id in RESOURCE_LOCALISATION_IDS:
        label = RESOURCE_TYPES.get(parameter, "")
        return replace_from_label_map(description, context["skill_tags"], label)
    if base_id in DAMAGE_LOCALISATION_IDS:
        label = DAMAGE_TYPES.get(parameter, "")
        return replace_from_label_map(description, context["ui_tooltips"], label)
    if base_id in CROWD_CONTROLLED_LOCALISATION_IDS:
        label = CROWD_CONTROLLED_TYPES.get(parameter, "")
        return replace_from_label_map(description, context["ui_tooltips"], label)
    if base_id in CROWD_CONTROL_LOCALISATION_IDS:
        label = CROWD_CONTROL_TYPES.get(parameter, "")
        return replace_from_label_map(description, context["ui_tooltips"], label)
    if base_id in WEAPON_TYPE_LOCALISATION_IDS:
        label = context["weapon_types_by_sno"].get(parameter, "")
        return replace_from_label_map(description, context["item_requirements"], label)
    if base_id in DOT_LOCALISATION_IDS:
        label = DOT_TYPES.get(parameter, "")
        return replace_from_label_map(description, context["ui_tooltips"], label)
    if base_id in NECRO_PET_LOCALISATION_IDS:
        label = NECRO_PET_NAMES.get(parameter, "")
        return replace_from_label_map(description, context["necromancer_army"], label)
    if base_id == "Damage_Percent_Bonus_Per_Shapeshift_Form":
        label = SHAPESHIFT_FORMS.get(parameter, "")
        return replace_from_label_map(description, context["ui_tooltips"], label)
    return description
