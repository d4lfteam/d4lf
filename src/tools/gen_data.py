# generate data from d4data repo
import json
import os
import re
from pathlib import Path

D4LF_BASE_DIR = Path(__file__).parent.parent.parent

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
        for x in ["(ph)", "[ph]", "[wip]", "(ptr)", "(debug)", "[_ph_]", "[ph_", "bucranis_", "boost_", "_test_", "(not_used", "(dns)"]
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


def main(d4data_dir: Path, companion_app_dir: Path):
    lang_arr = ["enUS"]  # "deDE", "frFR", "esES", "esMX", "itIT", "jaJP", "koKR", "plPL", "ptBR", "ruRU", "trTR", "zhCN", "zhTW"]

    for lang in lang_arr:
        file_names = [
            f"assets/lang/{lang}/affixes.json",
            f"assets/lang/{lang}/aspects.json",
            f"assets/lang/{lang}/uniques.json",
            f"assets/lang/{lang}/sigils.json",
            f"assets/lang/{lang}/tributes.json",
            f"assets/lang/{lang}/item_types.json",
            f"assets/lang/{lang}/tooltips.json",
        ]
        for f in file_names:
            if os.path.exists(f):
                os.remove(f)
        os.makedirs(f"assets/lang/{lang}", exist_ok=True)

    for language in lang_arr:
        # Create Aspects
        generate_aspects(d4data_dir, language)

        # Create Uniques
        generate_uniques(d4data_dir, language)

        print(f"Gen Sigils for {language}")
        sigil_dict = {"dungeons": {}, "minor": {}, "major": {}, "positive": {}}

        # Add others automatically
        pattern = f"json/{language}_Text/meta/StringList/World_DGN_*.stl.json"
        json_files = sorted(d4data_dir.glob(pattern, case_sensitive=False))
        for json_file in json_files:
            with open(json_file, encoding="utf-8") as file:
                data = json.load(file)
                name_idx, _ = (0, 1) if data["arStrings"][0]["szLabel"] == "Name" else (1, 0)
                dungeon_name: str = data["arStrings"][name_idx]["szText"].lower().strip().replace("’", "").replace("'", "")
                sigil_dict["dungeons"][dungeon_name.replace(" ", "_")] = dungeon_name

        pattern = f"json/{language}_Text/meta/StringList/DungeonAffix_*.stl.json"
        json_files = sorted(d4data_dir.glob(pattern, case_sensitive=False))
        for json_file in json_files:
            affix_type = json_file.stem.split("_")[1].lower().strip()
            if affix_type in sigil_dict:
                with open(json_file, encoding="utf-8") as file:
                    data = json.load(file)
                    name = ""
                    desc = ""
                    for sigil_affix in data["arStrings"]:
                        if sigil_affix["szLabel"] == "AffixName":
                            name = sigil_affix["szText"].lower().strip().replace("’", "").replace("'", "")
                            name = name.replace("(", "").replace(")", "")
                            name = remove_content_in_braces(name)
                        else:
                            desc = sigil_affix["szText"].lower().strip().replace("’", "").replace("'", "")
                            desc = remove_content_in_braces(desc)
                    sigil_dict[affix_type][name.replace(" ", "_")] = f"{name} {desc}"

        # Add any sigils we might be missing. Right now, that's none, but we leave the option for the future
        with open(D4LF_BASE_DIR / f"src/tools/data/custom_sigils_{language}.json", encoding="utf-8") as file:
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

        with open(D4LF_BASE_DIR / f"assets/lang/{language}/sigils.json", "w", encoding="utf-8") as json_file:
            json.dump(sigil_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
            json_file.write("\n")

        print(f"Gen Tributes for {language}")
        tribute_dict = {}

        # Add others automatically
        pattern = f"json/{language}_Text/meta/StringList/Item_*_TributeKeySigil_*.stl.json"
        json_files = sorted(d4data_dir.glob(pattern, case_sensitive=False))
        for json_file in json_files:
            with open(json_file, encoding="utf-8") as file:
                data = json.load(file)
                name_idx, _ = (0, 1) if data["arStrings"][0]["szLabel"] == "Name" else (1, 0)
                tribute_name: str = data["arStrings"][name_idx]["szText"].lower().strip().replace("’", "").replace("'", "")
                tribute_dict[tribute_name.replace(" ", "_").replace("(", "").replace(")", "")] = tribute_name

        with open(D4LF_BASE_DIR / f"assets/lang/{language}/tributes.json", "w", encoding="utf-8") as json_file:
            json.dump(tribute_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
            json_file.write("\n")

        print(f"Gen ItemTypes for {language}")
        whitelist_types = GEAR_TYPES.copy()
        whitelist_types.extend(["Elixir", "TemperManual", "Tome"])
        item_typ_dict = {"Material": "custom type material", "Sigil": "custom type sigil", "Incense": "custom type incense"}
        pattern = f"json/{language}_Text/meta/StringList/ItemType_*.stl.json"
        json_files = sorted(d4data_dir.glob(pattern, case_sensitive=False))
        for json_file in json_files:
            item_type = json_file.stem.split("_")[1].split(".")[0].strip()
            with open(json_file, encoding="utf-8") as file:
                data = json.load(file)
                name_idx = 0 if data["arStrings"][0]["szLabel"] == "Name" else 1
                name_str: str = check_ms(data["arStrings"][name_idx]["szText"]).lower().strip()
                if item_type in whitelist_types:
                    item_typ_dict[item_type] = name_str
        with open(D4LF_BASE_DIR / f"assets/lang/{language}/item_types.json", "w", encoding="utf-8") as json_file:
            json.dump(item_typ_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
            json_file.write("\n")

        print(f"Gen Tooltips for {language}")
        tooltip_dict = {}
        with open(d4data_dir / f"json/{language}_Text/meta/StringList/UIToolTips.stl.json", encoding="utf-8") as file:
            data = json.load(file)
            for arString in data["arStrings"]:
                if arString["szLabel"] == "ItemPower":
                    tooltip_dict["ItemPower"] = remove_content_in_braces(check_ms(arString["szText"].lower()))
        with open(D4LF_BASE_DIR / f"assets/lang/{language}/tooltips.json", "w", encoding="utf-8") as json_file:
            json.dump(tooltip_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
            json_file.write("\n")

        # Create Affixes
        print(f"Gen Affixes for {language}")
        affix_dict = {}
        with open(companion_app_dir / f"D4Companion/Data/Affixes.{language}.json", encoding="utf-8") as file:
            data = json.load(file)
            for affix in data:
                desc: str = affix["Description"]
                desc = desc.lower().strip().replace("'", "").replace("’", "").replace(".", "")
                desc = remove_content_in_braces(desc)
                name = desc.replace(",", "").replace(" ", "_")
                if len(desc) > 2:
                    affix_dict[name] = desc
        # Some of the unique specific affixes are missing. Add them manually
        with open(D4LF_BASE_DIR / f"src/tools/data/custom_affixes_{language}.json", encoding="utf-8") as file:
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
        with open(D4LF_BASE_DIR / f"assets/lang/{language}/affixes.json", "w", encoding="utf-8") as json_file:
            json.dump(affix_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
            json_file.write("\n")

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
        with open(core_aspect_file, encoding="utf-8") as aspect_file:
            # Get affix name from the file
            aspect_data = json.load(aspect_file)
            affix_name = aspect_data["snoAffix"]["name"]

        core_affix_file_name = f"Affix_{affix_name}.stl.json"
        core_affix_file = d4data_dir / f"json/{language}_Text/meta/StringList/{core_affix_file_name}"
        if not core_affix_file.exists():
            print(f"WARNING: Could not find file named {core_affix_file} in d4data.")

        with open(core_affix_file, encoding="utf-8") as file:
            data = json.load(file)
            name_idx = 0 if data["arStrings"][0]["szLabel"] == "Name" else 1
            aspect_name = data["arStrings"][name_idx]["szText"]
            aspect_name_clean = aspect_name.strip().replace(" ", "_").lower().replace("’", "").replace("'", "")
            aspect_name_clean = check_ms(aspect_name_clean)
            if is_placeholder_or_test_name(aspect_name_clean):
                continue
            aspects_list.append(aspect_name_clean)

    with open(D4LF_BASE_DIR / f"assets/lang/{language}/aspects.json", "w", encoding="utf-8") as json_file:
        aspects_list.sort()
        json.dump(aspects_list, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")


def generate_uniques(d4data_dir, language):
    items_to_ignore = ["halo", "pact_amulet", "wilted_potential"]

    print(f"Gen Uniques for {language}")
    unique_dict = {}
    unique_pattern = "json/base/meta/Item/*nique*.itm.json"
    unique_files = sorted(d4data_dir.glob(unique_pattern, case_sensitive=False))

    for core_unique_file in unique_files:
        # Get inherent count and item type from this file. Beyond that, we need the file name to find the enUS strings file.
        num_inherents = 0
        with open(core_unique_file, encoding="utf-8") as unique_item_file:
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
            with open(affix_file, encoding="utf-8") as unique_affix_file:
                affix_data = json.load(unique_affix_file)
                num_inherents += len(affix_data["ptItemAffixAttributes"])

        core_unique_file_id = core_unique_file.name.split(".")[0]
        string_item_file_name = f"Item_{core_unique_file_id}.stl.json"
        string_item_file = d4data_dir / f"json/{language}_Text/meta/StringList/{string_item_file_name}"

        if not string_item_file.exists():
            print(f"WARNING: Could not find file named {string_item_file} in d4data.")
            continue

        with open(string_item_file, encoding="utf-8") as file:
            data = json.load(file)
            name_item = [item for item in data["arStrings"] if item["szLabel"] == "Name"]
            if not name_item:
                continue
            name = name_item[0]["szText"]
            name_clean = name.strip().replace(" ", "_").replace("\xa0", "_").lower().replace("’", "").replace("'", "").replace(",", "")
            name_clean = check_ms(name_clean)
            if name_clean in items_to_ignore or is_placeholder_or_test_name(name_clean):
                continue

            # S10 This is a bit of a hack to handle some chaos uniques which for some reason report fewer inherents than they actually have
            if name_clean in unique_dict:
                continue

            unique_dict[name_clean] = {"num_inherents": num_inherents}

    with open(D4LF_BASE_DIR / f"assets/lang/{language}/uniques.json", "w", encoding="utf-8") as json_file:
        json.dump(unique_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Path Argument Parser")
    parser.add_argument("d4data_dir", type=str, help="Provide a path to d4data repo")  # https://github.com/DiabloTools/d4data.git
    parser.add_argument(
        "companion_app_dir", type=str, help="Provide a path to companion_app_dir repo"
    )  # https://github.com/josdemmers/Diablo4Companion
    args = parser.parse_args()

    input_path = Path(args.d4data_dir)
    input_path2 = Path(args.companion_app_dir)

    if input_path.exists() and input_path.is_dir() and input_path2.exists() and input_path2.is_dir():
        main(input_path, input_path2)
    else:
        print(f"The provided path '{input_path}' or '{input_path2}' does not exist or is not a directory.")
