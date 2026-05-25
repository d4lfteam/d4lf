# generate data from d4data repo
import json
import re
from pathlib import Path

D4LF_BASE_DIR = Path(__file__).parent.parent.parent

GEAR_ITEM_LABEL = 54
EXTRA_ITEM_TYPES = ("Elixir", "TemperManual", "Tome")
SIGIL_RARITY_COLOR_TAGS = {
    "c_white": "Common",
    "c_magic": "Magic",
    "c_rare": "Rare",
    "c_legendary": "Legendary",
    "c_mythic": "Mythic",
}


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


def get_string_list_name(string_list_file: Path) -> str | None:
    with string_list_file.open(encoding="utf-8") as file:
        data = json.load(file)
        name_item = [item for item in data["arStrings"] if item["szLabel"] == "Name"]
        if not name_item:
            return None
        return clean_item_name(name_item[0]["szText"])


def _load_gear_types(d4data_dir: Path) -> set[str]:
    item_type_pattern = "json/base/meta/ItemType/*.itt.json"
    item_type_files = sorted(d4data_dir.glob(item_type_pattern, case_sensitive=False))
    gear_types = set()

    for item_type_file in item_type_files:
        with Path(item_type_file).open(encoding="utf-8") as file:
            data = json.load(file)
        if GEAR_ITEM_LABEL in data.get("arItemLabels", []):
            gear_types.add(item_type_file.name.removesuffix(".itt.json"))

    return gear_types


def main(d4data_dir: Path, companion_app_dir: Path | None = None):
    lang_arr = [
        "enUS"
    ]  # "deDE", "frFR", "esES", "esMX", "itIT", "jaJP", "koKR", "plPL", "ptBR", "ruRU", "trTR", "zhCN", "zhTW"]
    gear_types = _load_gear_types(d4data_dir)
    item_type_whitelist = gear_types | set(EXTRA_ITEM_TYPES)

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
        generate_uniques(d4data_dir, language, gear_types)

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
                if item_type in item_type_whitelist:
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
        if companion_app_dir is None:
            generate_affixes(d4data_dir, language)
        else:
            generate_affixes_from_companion(companion_app_dir, language)
        print("=============================")


def generate_affixes_from_companion(companion_app_dir: Path, language: str):
    print(f"Gen Affixes for {language}")
    affix_dict = {}
    with Path(companion_app_dir / f"D4Companion/Data/Affixes.{language}.json").open(encoding="utf-8") as file:
        data = json.load(file)
        for affix in data:
            desc: str = affix["Description"]
            desc = desc.lower().strip().replace("'", "").replace("’", "").replace(".", "")
            desc = remove_content_in_braces(desc)
            desc = desc.removeprefix("x ")
            name = desc.replace(",", "").replace(" ", "_")
            if len(desc) > 2:
                affix_dict[name] = desc
    _add_custom_affixes(affix_dict, language)
    _write_affixes(affix_dict, language)


def generate_affixes(d4data_dir: Path, language: str):
    print(f"Gen Affixes for {language}")
    affix_files = _load_affix_files(d4data_dir)
    attribute_descriptions = _load_attribute_descriptions(d4data_dir, language)
    skill_tag_names = _load_skill_tag_names(d4data_dir)
    affix_tokens = _load_affix_tokens([name for name, _ in affix_files], skill_tag_names)
    affix_dict = {}

    for affix_name, affix_data in affix_files:
        description = _build_affix_description(
            affix_name=affix_name,
            affix_data=affix_data,
            attribute_descriptions=attribute_descriptions,
            power_names={},
            skill_tag_names=skill_tag_names,
            affix_tokens=affix_tokens,
        )
        if description is None:
            continue
        name = description.replace(",", "").replace(" ", "_")
        if len(description) > 2:
            affix_dict[name] = description

    _add_custom_affixes(affix_dict, language)
    _write_affixes(affix_dict, language)


def _add_custom_affixes(affix_dict: dict[str, str], language: str):
    with Path(D4LF_BASE_DIR / f"src/tools/data/custom_affixes_{language}.json").open(encoding="utf-8") as file:
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


def _write_affixes(affix_dict: dict[str, str], language: str):
    with Path(D4LF_BASE_DIR / f"assets/lang/{language}/affixes.json").open("w", encoding="utf-8") as json_file:
        json.dump(affix_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")


def _load_affix_files(d4data_dir: Path) -> list[tuple[str, dict]]:
    affix_pattern = "json/base/meta/Affix/*.aff.json"
    affix_files = sorted(d4data_dir.glob(affix_pattern, case_sensitive=False))
    result = []
    for affix_file in affix_files:
        with Path(affix_file).open(encoding="utf-8") as file:
            affix_data = json.load(file)
        result.append((affix_file.name.removesuffix(".aff.json"), affix_data))
    return result


def _load_attribute_descriptions(d4data_dir: Path, language: str) -> dict[str, str]:
    with Path(d4data_dir / f"json/{language}_Text/meta/StringList/AttributeDescriptions.stl.json").open(
        encoding="utf-8"
    ) as file:
        data = json.load(file)
    return {entry["szLabel"]: entry["szText"] for entry in data["arStrings"]}


def _load_skill_tag_names(d4data_dir: Path) -> dict[int, str]:
    skill_tag_file = d4data_dir / "json/base/meta/GameBalance/SkillTags.gam.json"
    with Path(skill_tag_file).open(encoding="utf-8") as file:
        data = json.load(file)

    skill_tag_names = {}
    for table in data["ptData"]:
        for entry in table["tEntries"]:
            header = entry["tHeader"]
            skill_tag_hash = header["szNameGBIDHash"]
            skill_tag_names[skill_tag_hash] = header["szName"]
            signed_hash = skill_tag_hash - 2**32 if skill_tag_hash >= 2**31 else skill_tag_hash
            skill_tag_names[signed_hash] = header["szName"]
    return skill_tag_names


def _load_affix_tokens(affix_names: list[str], skill_tag_names: dict[int, str]) -> dict[str, list[str]]:
    skill_tags = set(skill_tag_names.values())
    return {
        "damage": sorted(_extract_damage_tokens(affix_names, skill_tags), key=_token_sort_key),
        "resource": sorted(_extract_resource_tokens(affix_names), key=_token_sort_key),
        "resistance": sorted(_extract_resistance_tokens(skill_tags), key=_token_sort_key),
    }


def _extract_damage_tokens(affix_names: list[str], skill_tags: set[str]) -> set[str]:
    tokens = {tag.removeprefix("Damage_Override_") for tag in skill_tags if tag.startswith("Damage_Override_")}
    for affix_name in affix_names:
        for pattern in [
            r"^Damage_Type_Bonus_(?P<token>[A-Z][A-Za-z]*)(?:_|$)",
            r"^X2_DamageType_(?P<token>[A-Z][A-Za-z]*)(?:_|$)",
            r"^Tempered_Damage_Generic_Type_(?P<token>[A-Z][A-Za-z]*)(?:_|$)",
        ]:
            match = re.search(pattern, affix_name)
            if match is not None:
                tokens.add(match.group("token"))
    return tokens


def _extract_resource_tokens(affix_names: list[str]) -> set[str]:
    tokens = set()
    for affix_name in affix_names:
        for pattern in [
            r"(?:^|_)Resource_Max_?(?P<token>[A-Z][A-Za-z]*)(?:_|$)",
            r"(?:^|_)Resource_On_Kill_(?P<token>[A-Z][A-Za-z]*)(?:_|$)",
            r"(?:^|_)Resource_Per_Second_(?P<token>[A-Z][A-Za-z]*)(?:_|$)",
        ]:
            match = re.search(pattern, affix_name)
            if match is not None and match.group("token") != "AllClasses":
                tokens.add(match.group("token"))
    return tokens


def _extract_resistance_tokens(skill_tags: set[str]) -> set[str]:
    return {tag.removeprefix("Affix_Resistance_") for tag in skill_tags if tag.startswith("Affix_Resistance_")}


def _token_sort_key(token: str) -> tuple[str, str]:
    return (token.removeprefix("Non").lower(), token.lower())


def _build_affix_description(
    affix_name: str,
    affix_data: dict,
    attribute_descriptions: dict[str, str],
    power_names: dict[int, str],
    skill_tag_names: dict[int, str],
    affix_tokens: dict[str, list[str]],
) -> str | None:
    description_parts = []
    for affix_attribute in affix_data.get("ptItemAffixAttributes", []):
        attribute = affix_attribute.get("tAttribute", {})
        attribute_name = attribute.get("__eAttribute_name__", "")
        description = _find_attribute_description(attribute_name, attribute_descriptions)
        if description is None:
            continue
        description_parts.append(
            _replace_affix_description_parameters(
                description=description,
                affix_name=affix_name,
                attribute=attribute,
                power_names=power_names,
                skill_tag_names=skill_tag_names,
                affix_tokens=affix_tokens,
            )
        )

    if not description_parts:
        return None

    description = " ".join(description_parts).lower().strip().replace("'", "").replace("’", "").replace(".", "")
    description = remove_content_in_braces(description)
    return description.removeprefix("x ")


def _find_attribute_description(attribute_name: str, attribute_descriptions: dict[str, str]) -> str | None:
    description = attribute_descriptions.get(attribute_name)
    if description is not None:
        return description
    if "#" in attribute_name:
        return attribute_descriptions.get(attribute_name.split("#", maxsplit=1)[0])
    return None


def _replace_affix_description_parameters(
    description: str,
    affix_name: str,
    attribute: dict,
    power_names: dict[int, str],
    skill_tag_names: dict[int, str],
    affix_tokens: dict[str, list[str]],
) -> str:
    if "{VALUE1}" not in description:
        return description

    parameter = _find_affix_parameter(
        affix_name=affix_name,
        attribute=attribute,
        power_names=power_names,
        skill_tag_names=skill_tag_names,
        affix_tokens=affix_tokens,
    )
    return description.replace("{VALUE1}", parameter)


def _find_affix_parameter(
    affix_name: str,
    attribute: dict,
    power_names: dict[int, str],
    skill_tag_names: dict[int, str],
    affix_tokens: dict[str, list[str]],
) -> str:
    attribute_name = attribute.get("__eAttribute_name__", "")
    param = attribute.get("nParam")
    if isinstance(param, int):
        if attribute_name == "Skill_Rank_Bonus" and param in power_names:
            return power_names[param]
        if param in skill_tag_names:
            return _format_skill_tag_name(skill_tag_names[param])

    formula = attribute.get("gbidFormula") or {}
    formula_name = formula.get("name", "")
    if "DamageType" in formula_name or "Damage_Type" in attribute_name:
        return _find_named_token(affix_name, affix_tokens["damage"])
    if attribute_name == "Resistance":
        return _find_named_token(affix_name, affix_tokens["resistance"])
    if "Resource" in attribute_name:
        return _find_named_token(affix_name, affix_tokens["resource"])
    return _format_affix_name_token(affix_name)


def _find_named_token(affix_name: str, tokens: list[str]) -> str:
    for token in tokens:
        if token.lower() in affix_name.lower():
            return _humanize_token(token)
    return _format_affix_name_token(affix_name)


def _format_skill_tag_name(skill_tag_name: str) -> str:
    name = skill_tag_name
    for prefix in ["Skill_Primary_", "Skill_", "Affix_", "Damage_", "Tag_"]:
        name = name.removeprefix(prefix)
    name = name.replace("Category_", "")
    return _humanize_token(name)


def _format_affix_name_token(affix_name: str) -> str:
    name = affix_name.removeprefix("S04_")
    for prefix in [
        "SkillRankBonus_",
        "AttackSpeed_",
        "Damage_",
        "Resource_Max",
        "Resource_On_Kill_",
        "Resource_Per_Second_",
        "S04_Resource_Max_AllClasses_",
    ]:
        if name.startswith(prefix):
            name = name.removeprefix(prefix)
            break

    parts = [part for part in name.split("_") if part not in {"Barb", "Druid", "Generic", "Necro", "Rogue", "Sorc"}]
    if len(parts) > 1 and parts[0] in {"Basic", "Category", "Core", "Primary", "Special", "Special2", "Talent"}:
        parts = parts[1:]
    elif len(parts) > 2 and parts[1] in {"Basic", "Category", "Core", "Primary", "Special", "Special2", "Talent"}:
        parts = parts[2:]
    return _humanize_token("_".join(parts))


def _humanize_token(value: str) -> str:
    replacements = {
        "Basics": "Basic",
        "ColdImbue": "Cold Imbuement",
        "Earthspike": "Earth Spike",
        "HammeroftheAncients": "Hammer of the Ancients",
        "NonPhysical": "Nonphysical",
        "PoisonImbue": "Poison Imbuement",
        "ShadowImbue": "Shadow Imbuement",
    }
    value = replacements.get(value, value)
    value = value.replace("_", " ")
    value = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    return " ".join(value.split())


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


def generate_uniques(d4data_dir, language, gear_types: set[str]):
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

        if item_type not in gear_types:
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
    parser.add_argument(
        "companion_app_dir",
        nargs="?",
        type=Path,
        default=D4LF_BASE_DIR / "D4Companion",
        help="Provide a path to companion_app_dir repo",
    )  # https://github.com/josdemmers/Diablo4Companion
    args = parser.parse_args()

    input_path = args.d4data_dir
    input_path2 = args.companion_app_dir

    if input_path.exists() and input_path.is_dir() and (input_path2 is None or input_path2.is_dir()):
        main(input_path, input_path2)
    else:
        print(f"The provided path '{input_path}' or '{input_path2}' does not exist or is not a directory.")
