"""Affix data generation."""

import json
import re
from pathlib import Path
from typing import TypeVar

from src.tools.data_generation.affix_helpers import (
    replace_numeric_value_placeholders,
    replace_parameter_placeholder,
    update_affix_localisation_id,
)
from src.tools.data_generation.common import (
    D4LF_BASE_DIR,
    EXCLUDED_SEAL_AFFIX_KEYS,
    AffixData,
    AffixGenerationContext,
    AttributeReplacement,
    _is_nested_data,
    clean_item_name,
    load_json_file,
    remove_content_in_braces,
    string_list_map,
)
from src.tools.data_generation.constants import EXPECTED_MISSING_AFFIX_LOCALISATIONS

DataT = TypeVar("DataT")


def companion_style_affix_description(
    affix_data: AffixData, context: AffixGenerationContext, d4data_dir: Path, language: str
) -> str:
    affix_name = Path(affix_data["__fileName__"]).stem
    attributes: list[AttributeReplacement] = []
    for item_affix_attribute in affix_data.get("ptItemAffixAttributes") or []:
        attribute = item_affix_attribute.get("tAttribute")
        if attribute is None:
            continue
        localisation_id = attribute.get("__eAttribute_name__") or ""
        if not localisation_id:
            continue
        parameter = attribute.get("nParam", 0) % (2**32)
        formula = (attribute.get("szAttributeFormula") or {}).get("value", "")
        localisation_id = update_affix_localisation_id(
            localisation_id,
            parameter,
            context["attribute_descriptions"],
            context["attribute_prefixes"],
            context["power_by_sno"],
            context["skill_tags_by_sno"],
            context["weapon_types_by_sno"],
        )
        attributes.append({"formula": formula, "id": localisation_id, "parameter": parameter})

    description = ""
    for attribute in attributes:
        localisation = context["attribute_descriptions"].get(attribute["id"], "")
        if not localisation:
            if (affix_name, attribute["id"]) not in EXPECTED_MISSING_AFFIX_LOCALISATIONS:
                print(f"WARNING: ({affix_name}) Localisation id {attribute['id']} not found.")
            continue
        if not description or description != localisation:
            description += localisation

    description = replace_numeric_value_placeholders(description)
    for index, attribute in enumerate(attributes):
        if index > 0 and attribute["id"] == attributes[index - 1]["id"]:
            break
        if attribute["id"] == "Weapon_On_Hit_Percent_Bleed_Proc_Chance_Combined":
            for value_index, value_attribute in enumerate(attributes, start=1):
                description = description.replace(f"{{VALUE{value_index}}}", value_attribute["formula"])
        else:
            description = replace_parameter_placeholder(
                description, attribute["id"], attribute["parameter"], context, d4data_dir, language
            )

    return description


def normalise_affix_description(description: str) -> tuple[str, str] | None:
    desc = description.lower().strip().replace("'", "").replace("’", "").replace("â€™", "").replace(".", "")
    # A little hacky but we'll fix this bad data here. If we find more we'll make a better solution
    desc = desc.replace("lighting", "lightning")
    desc = remove_content_in_braces(desc)
    desc = desc.removeprefix("x ")
    if len(desc) <= 2:
        return None
    return desc.replace(",", "").replace(" ", "_"), desc


def affix_string_description(
    affix_name: str, string_list_dir: Path, strip_prefix_pattern: str | None = None
) -> str | None:
    string_list_file = string_list_dir / f"Affix_{affix_name}.stl.json"
    if not string_list_file.exists():
        return None

    description = string_list_map(string_list_file).get("Desc", "")
    if not description:
        return None

    if strip_prefix_pattern is not None:
        return re.sub(strip_prefix_pattern, "", description, count=1)
    return description


def generate_affixes(d4data_dir: Path, language: str, output_file: Path | None = None):
    print(f"Gen Affixes for {language} (This one takes a while)")
    core_toc = load_json_file(d4data_dir / "json/base/CoreTOC.dat.json")
    gbid = load_json_file(d4data_dir / "json/GBID.json")
    string_list_dir = d4data_dir / f"json/{language}_Text/meta/StringList"
    attribute_descriptions = string_list_map(string_list_dir / "AttributeDescriptions.stl.json")
    context: AffixGenerationContext = {
        "attribute_descriptions": attribute_descriptions,
        "attribute_prefixes": {label.split("#", maxsplit=1)[0] for label in attribute_descriptions if "#" in label},
        "item_requirements": string_list_map(string_list_dir / "ItemRequirements.stl.json"),
        "necromancer_army": string_list_map(string_list_dir / "NecromancerArmy.stl.json"),
        "skill_tags": string_list_map(string_list_dir / "SkillTags.stl.json"),
        "ui_tooltips": string_list_map(string_list_dir / "UIToolTips.stl.json"),
        "power_by_sno": {
            int(power_data["__snoID__"]): power_data["__fileName__"]
            for power_data in (
                load_json_file(power_file)
                for power_file in sorted((d4data_dir / "json/base/meta/Power").glob("*.json"))
            )
        },
        "skill_tags_by_sno": {int(key) % (2**32): value for key, value in core_toc.get("56", {}).items()},
        "weapon_types_by_sno": {int(key) % (2**32): value for key, value in core_toc.get("116", {}).items()},
    }
    if not context["skill_tags_by_sno"]:
        context["skill_tags_by_sno"] = {int(key) % (2**32): value for key, value in gbid.get("56", {}).items()}

    affix_dict = {}
    seal_dict = {}
    charm_dict = {}
    affix_pattern = "json/base/meta/Affix/*.json"
    affix_files = sorted(d4data_dir.glob(affix_pattern, case_sensitive=False))
    for affix_file in affix_files:
        affix_data = load_json_file(affix_file)
        affix_name = Path(affix_data["__fileName__"]).stem
        is_seal_affix = affix_name.startswith("Talisman_SealAffix_")
        is_charm_affix = affix_name.startswith("Talisman_Charm_")
        if affix_data.get("eMagicType") != 0 and not is_seal_affix:
            continue
        if affix_name.startswith("zz"):
            continue
        if "_Resistance_" in affix_name and "_Dual_" in affix_name:
            continue
        if affix_name.casefold() == "2HStaff_Unique_AF_001_Int_Decrease".casefold():
            continue
        description = None
        if is_seal_affix or is_charm_affix:
            description = affix_string_description(affix_name, string_list_dir)
        if description is None:
            if affix_data.get("eMagicType") != 0 or not affix_data.get("ptItemAffixAttributes"):
                continue
            description = companion_style_affix_description(affix_data, context, d4data_dir, language)
        normalised = normalise_affix_description(description)
        if normalised is None:
            continue
        key, value = normalised
        if is_seal_affix and (
            key in EXCLUDED_SEAL_AFFIX_KEYS
            or (key.startswith("while_at_least_") and "_charms_equipped_" in key)
            or "_charm_equipped_" in key
        ):
            continue
        if is_seal_affix:
            seal_dict[key] = value
        elif is_charm_affix:
            charm_dict[key] = value
        else:
            affix_dict[key] = value

    merge_custom_data(affix_dict, "affixes", language)
    merge_custom_data(seal_dict, "seals_affixes", language)
    merge_custom_data(charm_dict, "charms_affixes", language)

    output_path = output_file or D4LF_BASE_DIR / f"assets/lang/{language}/affixes.json"
    with output_path.open("w", encoding="utf-8") as json_file:
        json.dump(affix_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")

    seal_output_path = D4LF_BASE_DIR / f"assets/lang/{language}/seals_affixes.json"
    with seal_output_path.open("w", encoding="utf-8") as json_file:
        json.dump(seal_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")

    charm_output_path = D4LF_BASE_DIR / f"assets/lang/{language}/charms_affixes.json"
    with charm_output_path.open("w", encoding="utf-8") as json_file:
        json.dump(charm_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")


def merge_custom_data(data: list[DataT] | dict[str, DataT], name: str, language: str) -> None:
    """Merge entries from a custom override file into the generated data.

    Reads the *name* section from a single ``src/tools/data/custom_<language>.json``
    file.  The file groups all custom overrides by target (e.g. ``"affixes"``,
    ``"sigils"``, ``"aspects"``).

    Supports three data shapes:
    - **list**: custom entries are appended (duplicates skipped with a warning).
    - **flat dict**: custom key/value pairs are merged (conflicts logged).
    - **nested dict** (dict of dicts): merges one level deep (e.g. sigils).

    If the file does not exist or the section is missing, the call is a no-op.
    """
    custom_file = D4LF_BASE_DIR / f"src/tools/data/custom_{language}.json"
    if not custom_file.exists():
        return
    with custom_file.open(encoding="utf-8") as file:
        all_custom = json.load(file)

    custom = all_custom.get(name)
    if custom is None:
        return

    if isinstance(data, list):
        _merge_list(data, custom, name)
    elif _is_nested_data(data) and _is_nested_data(custom) and custom:
        _merge_nested_dict(data, custom, name)
    elif isinstance(data, dict):
        _merge_flat_dict(data, custom, name)


def _merge_list(data: list[DataT], custom: list[DataT], name: str) -> None:
    existing = set(data)
    for entry in custom:
        if entry in existing:
            print(f"{name}: '{entry}' already exists. Can be deleted from custom json")
        else:
            data.append(entry)


def _merge_flat_dict(data: dict[str, DataT], custom: dict[str, DataT], name: str) -> None:
    for key, value in custom.items():
        if key in data:
            if data[key] == value:
                print(f"{name}: '{key}' already exists. Can be deleted from custom json")
            else:
                print(f"{name}: '{key}' already exists but with different value")
                data[key] = value
        else:
            data[key] = value


def _merge_nested_dict(data: dict[str, dict[str, DataT]], custom: dict[str, dict[str, DataT]], name: str) -> None:
    for section, entries in custom.items():
        if section not in data:
            data[section] = entries
            continue
        current = data[section]
        for key, value in entries.items():
            if key in current:
                if current[key] == value:
                    print(f"{name}: '{key}' in '{section}' already exists. Can be deleted from custom json")
                else:
                    print(f"{name}: '{key}' in '{section}' already exists but with different value")
                    current[key] = value
            else:
                current[key] = value


def get_string_list_name(string_list_file: Path) -> str | None:
    with string_list_file.open(encoding="utf-8") as file:
        data = json.load(file)
        name_item = [item for item in data["arStrings"] if item["szLabel"] == "Name"]
        if not name_item:
            return None
        return clean_item_name(name_item[0]["szText"])
