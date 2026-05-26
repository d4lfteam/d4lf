# generate data from d4data repo
import json
import re
from pathlib import Path
from typing import TypedDict

from src.tools.gen_data_helpers import (
    CROWD_CONTROL_LOCALISATION_IDS,
    CROWD_CONTROL_TYPES,
    CROWD_CONTROLLED_LOCALISATION_IDS,
    CROWD_CONTROLLED_TYPES,
    DAMAGE_LOCALISATION_IDS,
    DAMAGE_TYPES,
    DOT_LOCALISATION_IDS,
    DOT_TYPES,
    EXPECTED_MISSING_AFFIX_LOCALISATIONS,
    LOCALISATION_ID_RENAMES,
    NECRO_PET_LOCALISATION_IDS,
    NECRO_PET_NAMES,
    POWER_LOCALISATION_IDS,
    POWER_SUB_LOCALISATION_IDS,
    RESISTANCE_TYPES,
    RESOURCE_LOCALISATION_IDS,
    RESOURCE_TYPES,
    SHAPESHIFT_FORMS,
    SIGIL_RARITY_COLOR_TAGS,
    SKILL_TAG_LOCALISATION_IDS,
    SKILL_TAG_SUB_LOCALISATION_IDS,
    WEAPON_TYPE_LOCALISATION_IDS,
)

D4LF_BASE_DIR = Path(__file__).parent.parent.parent


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


GEAR_TYPES = [
    "Amulet",
    "Axe",
    "Axe2H",
    "Boots",
    "Bow",
    "ChestArmor",
    "Crossbow2H",
    "Dagger",
    "Flail",
    "Focus",
    "Glaive",
    "Gloves",
    "Helm",
    "Legs",
    "Mace",
    "Mace2H",
    "OffHandTotem",
    "Polearm",
    "Quarterstaff",
    "Ring",
    "Scythe",
    "Scythe2H",
    "Shield",
    "Staff",
    "Sword",
    "Sword2H",
    "Wand",
]


def remove_content_in_braces(input_string) -> str:
    pattern = r"\{.*?\}"
    result = re.sub(pattern, "", input_string)
    pattern = r"\[.*?\]"
    result = re.sub(pattern, "", result)
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


def get_random_number_idx(s: str) -> list[int]:
    filtered_string = re.findall(r"\{c_random\}|\{c_number\}", s)
    res = []
    for i, val in enumerate(filtered_string):
        if val == "{c_random}":
            res.append(i)
    return res


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


def localise(label_map: dict[str, str], label: str) -> str:
    return label_map.get(label, "")


def get_power_id(power_by_sno: dict[int, str], sno: int) -> str:
    power_file_name = power_by_sno.get(sno, "")
    return Path(power_file_name).stem


def get_first_gbid_name(gbid_by_sno: dict[int, list[str]], sno: int) -> str:
    names = gbid_by_sno.get(sno, [])
    return names[0] if names else ""


def dot_damage_type_id(sno: int) -> str:
    return {0: "Physical", 1: "Fire", 4: "Poison", 5: "Shadow"}.get(sno, "")


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
        sub_id = dot_damage_type_id(parameter)
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
    value = localise(label_map, label)
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

    skill_name = localise(string_list_map(power_string_file), "name")
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


def replace_formula_values(description: str, attributes: list[dict]) -> str:
    for index, attribute in enumerate(attributes, start=1):
        description = description.replace(f"{{VALUE{index}}}", attribute["formula"])
    return description


def companion_style_affix_description(
    affix_data: dict, context: AffixGenerationContext, d4data_dir: Path, language: str
) -> str:
    affix_name = Path(affix_data["__fileName__"]).stem
    attributes = []
    for item_affix_attribute in affix_data.get("ptItemAffixAttributes") or []:
        attribute = item_affix_attribute.get("tAttribute") or {}
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
        localisation = localise(context["attribute_descriptions"], attribute["id"])
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
            description = replace_formula_values(description, attributes)
        else:
            description = replace_parameter_placeholder(
                description, attribute["id"], attribute["parameter"], context, d4data_dir, language
            )

    return description


def normalise_affix_description(description: str) -> tuple[str, str] | None:
    desc = description.lower().strip().replace("'", "").replace("’", "").replace("â€™", "").replace(".", "")
    desc = remove_content_in_braces(desc)
    desc = desc.removeprefix("x ")
    if len(desc) <= 2:
        return None
    return desc.replace(",", "").replace(" ", "_"), desc


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
    affix_pattern = "json/base/meta/Affix/*.json"
    affix_files = sorted(d4data_dir.glob(affix_pattern, case_sensitive=False))
    for affix_file in affix_files:
        affix_data = load_json_file(affix_file)
        affix_name = Path(affix_data["__fileName__"]).stem
        if affix_data.get("eMagicType") != 0:
            continue
        if affix_name.startswith("zz"):
            continue
        if "_Resistance_" in affix_name and "_Dual_" in affix_name:
            continue
        if affix_name.casefold() == "2HStaff_Unique_AF_001_Int_Decrease".casefold():
            continue
        if not affix_data.get("ptItemAffixAttributes"):
            continue

        description = companion_style_affix_description(affix_data, context, d4data_dir, language)
        normalised = normalise_affix_description(description)
        if normalised is None:
            continue
        key, value = normalised
        affix_dict[key] = value

    merge_custom_affixes(affix_dict, language)
    output_path = output_file or D4LF_BASE_DIR / f"assets/lang/{language}/affixes.json"
    with output_path.open("w", encoding="utf-8") as json_file:
        json.dump(affix_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")


def merge_custom_affixes(affix_dict: dict[str, str], language: str):
    custom_affixes_file = D4LF_BASE_DIR / f"src/tools/data/custom_affixes_{language}.json"
    with custom_affixes_file.open(encoding="utf-8") as file:
        data = json.load(file)
        for key, value in data.items():
            if key in affix_dict:
                if affix_dict[key] == value:
                    print(f"Affix {key} already exists in affixes.json. Can be deleted from custom json")
                else:
                    print(f"Affix {key} already exists in affixes.json but with different value")
                    affix_dict[key] = value
            else:
                affix_dict[key] = value


def get_string_list_name(string_list_file: Path) -> str | None:
    with string_list_file.open(encoding="utf-8") as file:
        data = json.load(file)
        name_item = [item for item in data["arStrings"] if item["szLabel"] == "Name"]
        if not name_item:
            return None
        return clean_item_name(name_item[0]["szText"])


def main(d4data_dir: Path):
    lang_arr = [
        "enUS"
    ]  # "deDE", "frFR", "esES", "esMX", "itIT", "jaJP", "koKR", "plPL", "ptBR", "ruRU", "trTR", "zhCN", "zhTW"]

    for lang in lang_arr:
        file_names = [
            f"assets/lang/{lang}/affixes.json",
            f"assets/lang/{lang}/aspects.json",
            f"assets/lang/{lang}/sets.json",
            f"assets/lang/{lang}/uniques.json",
            f"assets/lang/{lang}/sigils.json",
            f"assets/lang/{lang}/tributes.json",
            f"assets/lang/{lang}/item_types.json",
            f"assets/lang/{lang}/tooltips.json",
        ]
        for f in file_names:
            if Path(f).exists():
                Path(f).unlink()
        Path(f"assets/lang/{lang}").mkdir(exist_ok=True, parents=True)

    for language in lang_arr:
        # Create Aspects
        generate_aspects(d4data_dir, language)

        # Create Uniques
        generate_uniques(d4data_dir, language)

        # Create Sets
        generate_sets(d4data_dir, language)

        # Create Sigils
        generate_sigils(d4data_dir, language)

        print(f"Gen Tributes for {language}")
        tribute_dict = {}

        # Add others automatically
        pattern = f"json/{language}_Text/meta/StringList/Item_*_TributeKeySigil_*.stl.json"
        json_files = sorted(d4data_dir.glob(pattern, case_sensitive=False))
        for json_file in json_files:
            with Path(json_file).open(encoding="utf-8") as file:
                data = json.load(file)
                name_idx, _ = (0, 1) if data["arStrings"][0]["szLabel"] == "Name" else (1, 0)
                tribute_name: str = (
                    data["arStrings"][name_idx]["szText"].lower().strip().replace("’", "").replace("'", "")
                )
                tribute_dict[tribute_name.replace(" ", "_").replace("(", "").replace(")", "")] = tribute_name

        with Path(D4LF_BASE_DIR / f"assets/lang/{language}/tributes.json").open("w", encoding="utf-8") as json_file:
            json.dump(tribute_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
            json_file.write("\n")

        print(f"Gen ItemTypes for {language}")
        whitelist_types = GEAR_TYPES.copy()
        whitelist_types.extend(["Elixir", "TemperManual", "Tome"])
        item_typ_dict = {
            "Material": "custom type material",
            "Sigil": "custom type sigil",
            "Incense": "custom type incense",
        }
        pattern = f"json/{language}_Text/meta/StringList/ItemType_*.stl.json"
        json_files = sorted(d4data_dir.glob(pattern, case_sensitive=False))
        for json_file in json_files:
            item_type = json_file.stem.split("_")[1].split(".")[0].strip()
            with Path(json_file).open(encoding="utf-8") as file:
                data = json.load(file)
                name_idx = 0 if data["arStrings"][0]["szLabel"] == "Name" else 1
                name_str: str = check_ms(data["arStrings"][name_idx]["szText"]).lower().strip()
                if item_type in whitelist_types:
                    item_typ_dict[item_type] = name_str
        with Path(D4LF_BASE_DIR / f"assets/lang/{language}/item_types.json").open("w", encoding="utf-8") as json_file:
            json.dump(item_typ_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
            json_file.write("\n")

        print(f"Gen Tooltips for {language}")
        tooltip_dict = {}
        with Path(d4data_dir / f"json/{language}_Text/meta/StringList/UIToolTips.stl.json").open(
            encoding="utf-8"
        ) as file:
            data = json.load(file)
            for arString in data["arStrings"]:
                if arString["szLabel"] == "ItemPower":
                    tooltip_dict["ItemPower"] = remove_content_in_braces(check_ms(arString["szText"].lower()))
        with Path(D4LF_BASE_DIR / f"assets/lang/{language}/tooltips.json").open("w", encoding="utf-8") as json_file:
            json.dump(tooltip_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
            json_file.write("\n")

        # Create Affixes
        generate_affixes(d4data_dir, language)

        print("=============================")


def generate_aspects(d4data_dir, language):
    print(f"Gen Aspects for {language}")
    aspects_list = []
    aspect_pattern = "json/base/meta/Aspect/*.json"
    aspect_files = sorted(d4data_dir.glob(aspect_pattern, case_sensitive=False))

    for core_aspect_file in aspect_files:
        if core_aspect_file.name.endswith("Axe Bad Data.asp.json"):
            continue
        # Get the associated Aspect file, which will tell us where to find the aspect file
        with Path(core_aspect_file).open(encoding="utf-8") as aspect_file:
            # Get affix name from the file
            aspect_data = json.load(aspect_file)
            affix_name = aspect_data["snoAffix"]["name"]

        core_affix_file_name = f"Affix_{affix_name}.stl.json"
        core_affix_file = d4data_dir / f"json/{language}_Text/meta/StringList/{core_affix_file_name}"
        if not core_affix_file.exists():
            print(f"WARNING: Could not find file named {core_affix_file} in d4data.")

        aspect_name_clean = get_string_list_name(core_affix_file)
        if aspect_name_clean is None or is_placeholder_or_test_name(aspect_name_clean):
            continue
        aspects_list.append(aspect_name_clean)

    with Path(D4LF_BASE_DIR / f"assets/lang/{language}/aspects.json").open("w", encoding="utf-8") as json_file:
        aspects_list.sort()
        json.dump(aspects_list, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")


def generate_sigils(d4data_dir, language):
    print(f"Gen Sigils for {language}")
    sigil_dict = {"dungeons": {}, "minor": {}, "major": {}, "positive": {}}
    sigil_rarity_dict = {}
    string_list_dir = d4data_dir / f"json/{language}_Text/meta/StringList"

    pattern = "json/base/meta/World/DGN_*.wrl.json"
    json_files = sorted(d4data_dir.glob(pattern, case_sensitive=False))
    for json_file in json_files:
        world_file_id = json_file.name.removesuffix(".wrl.json")
        string_list_file = string_list_dir / f"World_{world_file_id}.stl.json"
        if not string_list_file.exists():
            print(f"WARNING: Could not find string list for dungeon world {json_file}.")
            continue

        dungeon_name_key = get_string_list_name(string_list_file)
        if dungeon_name_key is None:
            continue
        sigil_dict["dungeons"][dungeon_name_key] = dungeon_name_key.replace("_", " ")

    pattern = "json/base/meta/DungeonAffix/*.dax.json"
    json_files = sorted(d4data_dir.glob(pattern, case_sensitive=False))
    for json_file in json_files:
        dungeon_affix_file_id = json_file.name.removesuffix(".dax.json")
        affix_type = dungeon_affix_file_id.split("_", maxsplit=1)[0].lower().strip()
        if affix_type not in sigil_dict or affix_type == "dungeons":
            continue

        string_list_file = string_list_dir / f"DungeonAffix_{dungeon_affix_file_id}.stl.json"
        if not string_list_file.exists():
            print(f"WARNING: Could not find string list for dungeon affix {json_file}.")
            continue

        with Path(string_list_file).open(encoding="utf-8") as file:
            data = json.load(file)
            raw_name = string_list_value(data, "AffixName")
            rarity = extract_sigil_rarity(raw_name)
            name = remove_content_in_braces(raw_name).replace("(", "").replace(")", "")
            desc = string_list_value(data, "AffixDesc").lower().strip().replace("’", "").replace("'", "")
            desc = remove_content_in_braces(desc)
            sigil_name_key = clean_item_name(name)
            sigil_dict[affix_type][sigil_name_key] = f"{sigil_name_key.replace('_', ' ')} {desc}"
            if rarity:
                sigil_rarity_dict[sigil_name_key] = rarity

    # Add any sigils we might be missing. Right now, that's none, but we leave the option for the future
    with Path(D4LF_BASE_DIR / f"src/tools/data/custom_sigils_{language}.json").open(encoding="utf-8") as file:
        data = json.load(file)
        for key, values in data.items():
            if key in sigil_dict:
                for key2, value2 in values.items():
                    if key2 in sigil_dict[key]:
                        if sigil_dict[key][key2] == value2:
                            print(f"Sigil {key2} already exists in sigils.json. Can be deleted from custom json")
                        else:
                            print(f"Sigil {key2} already exists in sigils.json but with different value")
                            sigil_dict[key][key2] = value2
                    else:
                        sigil_dict[key][key2] = value2
            else:
                sigil_dict[key] = values

    sigil_dict["rarities"] = sigil_rarity_dict

    with Path(D4LF_BASE_DIR / f"assets/lang/{language}/sigils.json").open("w", encoding="utf-8") as json_file:
        json.dump(sigil_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")


def string_list_value(data, label):
    for entry in data["arStrings"]:
        if entry["szLabel"] == label:
            return entry["szText"]
    return ""


def extract_sigil_rarity(name):
    for color_tag, rarity in SIGIL_RARITY_COLOR_TAGS.items():
        if f"{{{color_tag}}}" in name:
            return rarity
    return None


def generate_uniques(d4data_dir, language):
    items_to_ignore = ["halo", "pact_amulet", "wilted_potential"]

    print(f"Gen Uniques for {language}")
    unique_dict = {}
    unique_pattern = "json/base/meta/Item/*nique*.itm.json"
    unique_files = sorted(d4data_dir.glob(unique_pattern, case_sensitive=False))

    for core_unique_file in unique_files:
        if core_unique_file.name.startswith("S10_"):
            # Chaos uniques really throw off our inherent counts
            continue
        # Get inherent count and item type from this file. Beyond that, we need the file name to find the enUS strings file.
        num_inherents = 0
        with Path(core_unique_file).open(encoding="utf-8") as unique_item_file:
            unique_item_data = json.load(unique_item_file)
            if "arForcedAffixes" not in unique_item_data or not unique_item_data["arForcedAffixes"]:
                continue
            item_type = unique_item_data["snoItemType"]["name"]
            inherent_affixes = unique_item_data["arInherentAffixes"]

        if item_type not in GEAR_TYPES and item_type != "FocusBookOffHand":
            continue

        # Some items, like Mortacrux, will list one inherent and then break it into two in the affix file.
        # We will use the affix file for the true inherent count.
        for inherent_affix in inherent_affixes:
            # Inexplicably this inherent is broken into two when it's just 1
            if inherent_affix["name"].startswith("UNIQUE_INHERENT_Evade_MovementSpeed_"):
                num_inherents += 1
                continue
            affix_file_path = inherent_affix["__targetFileName__"]
            affix_file = d4data_dir / f"json/{affix_file_path}.json"
            with Path(affix_file).open(encoding="utf-8") as unique_affix_file:
                affix_data = json.load(unique_affix_file)
                num_inherents += len(affix_data["ptItemAffixAttributes"])

        core_unique_file_id = core_unique_file.name.split(".")[0]
        string_item_file_name = f"Item_{core_unique_file_id}.stl.json"
        string_item_file = d4data_dir / f"json/{language}_Text/meta/StringList/{string_item_file_name}"

        if not string_item_file.exists():
            print(f"WARNING: Could not find file named {string_item_file} in d4data.")
            continue

        name_clean = get_string_list_name(string_item_file)
        if name_clean is None or name_clean in items_to_ignore or is_placeholder_or_test_name(name_clean):
            continue

        unique_dict[name_clean] = {"num_inherents": num_inherents}

    with Path(D4LF_BASE_DIR / f"assets/lang/{language}/uniques.json").open("w", encoding="utf-8") as json_file:
        json.dump(unique_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")


def generate_sets(d4data_dir, language):
    print(f"Gen Sets for {language}")
    sets_list = []
    charm_pattern = "json/base/meta/Item/Talisman_Charm*.itm.json"
    charm_files = sorted(d4data_dir.glob(charm_pattern, case_sensitive=False))

    for charm_file in charm_files:
        with charm_file.open(encoding="utf-8") as file:
            charm_data = json.load(file)

        if charm_data["snoItemType"]["name"] != "Charm":
            continue

        set_item_bonus = charm_data.get("snoSetItemBonus")
        if not set_item_bonus:
            continue

        set_name = set_item_bonus["name"]
        string_set_file = d4data_dir / f"json/{language}_Text/meta/StringList/SetItemBonus_{set_name}.stl.json"
        if not string_set_file.exists():
            print(f"WARNING: Could not find file named {string_set_file} in d4data.")
            continue

        set_name_clean = get_string_list_name(string_set_file)
        if set_name_clean is None or is_placeholder_or_test_name(set_name_clean):
            continue
        sets_list.append(set_name_clean)

    sets_list = sorted(set(sets_list))
    with Path(D4LF_BASE_DIR / f"assets/lang/{language}/sets.json").open("w", encoding="utf-8") as json_file:
        json.dump(sets_list, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Path Argument Parser")
    parser.add_argument(
        "d4data_dir", nargs="?", type=Path, default=D4LF_BASE_DIR / "d4data", help="Provide a path to d4data repo"
    )  # https://github.com/DiabloTools/d4data.git
    args = parser.parse_args()

    input_path = args.d4data_dir

    if input_path.exists() and input_path.is_dir():
        main(input_path)
    else:
        print(f"The provided path '{input_path}' does not exist or is not a directory.")
