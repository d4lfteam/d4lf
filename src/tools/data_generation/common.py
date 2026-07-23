"""Shared data-generation parsing helpers."""

import json
import re
from pathlib import Path
from typing import TypedDict, TypeGuard, TypeVar

D4LF_BASE_DIR = Path(__file__).parents[3]

EXCLUDED_SEAL_AFFIX_KEYS = {
    "when_you_gain_a_stack_of_stoicism_gain_damage_for_second",
    "while_in_a_feral_rage_your_werewolf_skills_gain_attack_speed",
    "cannot_have_more_than_sockets_but_can_equip_unique_charms",
}


class AffixGenerationContext(TypedDict):
    attribute_descriptions: dict[str, str]
    attribute_prefixes: set[str]
    item_requirements: dict[str, str]
    necromancer_army: dict[str, str]
    power_by_sno: dict[int, str]
    skill_tags: dict[str, str]
    skill_tags_by_sno: dict[int, list[str]]
    ui_tooltips: dict[str, str]
    weapon_types_by_sno: dict[int, str]
    power_names_by_id: dict[str, str]


class AffixFormula(TypedDict):
    value: str


class AffixAttribute(TypedDict, total=False):
    __eAttribute_name__: str
    nParam: int
    szAttributeFormula: AffixFormula


class AffixAttributeEntry(TypedDict, total=False):
    tAttribute: AffixAttribute


class AffixData(TypedDict, total=False):
    __fileName__: str
    eMagicType: int
    ptItemAffixAttributes: list[AffixAttributeEntry]


class AttributeReplacement(TypedDict):
    formula: str
    id: str
    parameter: int


DataT = TypeVar("DataT")


def _is_nested_data(value: object) -> TypeGuard[dict[str, dict[str, DataT]]]:
    return isinstance(value, dict) and all(
        isinstance(key, str) and isinstance(item, dict) for key, item in value.items()
    )


def remove_content_in_braces(input_string) -> str:
    pattern = r"\{.*?\}"
    result = re.sub(pattern, "", input_string)
    pattern = r"\[.*?\]"
    result = re.sub(pattern, "", result)
    result = re.sub(r"\([^()]*#%[^()]*\)", "", result)
    result = re.sub(r"#%.*?#%", "", result)
    result = re.sub(r"\|.*?:", "|:", result)
    result = result.replace("|", "")
    result = result.replace(";", "")
    result = re.sub(r"(\d)[, ]+(\d)", r"\1\2", result)  # Remove , between numbers (large number seperator)
    result = re.sub(r"(\+)?\d+(\.\d+)?%?", "", result)  # Remove numbers and trailing % or preceding +
    result = re.sub(r"[\[\]+\-:%\'\#]", "", result)  # Remove [ and ] and leftover +, -, %, :, ', #
    result = " ".join(result.split())  # Remove extra spaces
    result.strip()
    return result


def is_placeholder_or_test_name(name) -> bool:
    if any(
        x in name
        for x in [
            "(ph)",
            "[ph]",
            "[wip]",
            "(ptr)",
            "(debug)",
            "[_ph_]",
            "[ph_",
            "bucranis_",
            "boost_",
            "_test_",
            "(not_used",
            "(dns)",
            "(crucible)",
            "(redesign)",
        ]
    ):
        return True

    return name.startswith("ph_")


def check_ms(input_string) -> str:
    start_index = input_string.find("[ms]")
    end_index = input_string.find("[fs]")

    # Check if both "[ms]" and "[fs]" are present
    if start_index != -1 and end_index != -1:
        # Extract the part between "[ms]" and "[fs]"
        input_string = input_string[start_index + 4 : end_index]

    prefixes = ["[ms]", "[ns]", "[fs]", "[p]"]
    for prefix in prefixes:
        if input_string.startswith(prefix):
            input_string = input_string[len(prefix) :]
            break

    return input_string.replace("{d}", "")


def clean_item_name(name: str) -> str:
    clean_name = (
        name
        .strip()
        .replace(" ", "_")
        .replace("\xa0", "_")
        .lower()
        .replace("’", "")
        .replace("â€™", "")
        .replace("'", "")
        .replace(",", "")
    )
    return check_ms(clean_name)


def load_json_file(json_file: Path):
    with json_file.open(encoding="utf-8") as file:
        return json.load(file)


def string_list_map(string_list_file: Path) -> dict[str, str]:
    data = load_json_file(string_list_file)
    return {entry["szLabel"]: entry["szText"] for entry in data["arStrings"]}


def get_power_id(power_by_sno: dict[int, str], sno: int) -> str:
    power_file_name = power_by_sno.get(sno, "")
    return Path(power_file_name).stem


def get_first_gbid_name(gbid_by_sno: dict[int, list[str]], sno: int) -> str:
    names = gbid_by_sno.get(sno, [])
    return names[0] if names else ""
