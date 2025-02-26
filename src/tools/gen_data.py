# generate data from d4data repo
import json
import os
import re
from pathlib import Path

D4LF_BASE_DIR = Path(__file__).parent.parent.parent


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
        # Create Uniques
        print(f"Gen Uniques for {language}")
        unique_dict = {}
        potential_custom_uniques = {}
        pattern = f"json/{language}_Text/meta/StringList/Item_*_Unique_*.stl.json"
        json_files = list(d4data_dir.glob(pattern))
        for json_file in json_files:
            with open(json_file, encoding="utf-8") as file:
                data = json.load(file)
                name_item = [item for item in data["arStrings"] if item["szLabel"] == "Name"]
                if not name_item:
                    continue
                name = name_item[0]["szText"]
                name_clean = name.strip().replace(" ", "_").lower().replace("’", "").replace("'", "").replace(",", "")
                name_clean = check_ms(name_clean)
                # Open affix file for affix
                splits = json_file.name.split("_")
                affix_file_name = "Affix_" + "_".join(splits[1:])
                affix_file_path = json_file.parent / affix_file_name
                if not affix_file_path.exists():
                    if not any(string_to_skip in name_clean for string_to_skip in ["[ph]", "(ph)", "ph_", "_test_", "debug"]) and not any(
                        string_to_skip in affix_file_name
                        for string_to_skip in ["S07_Witch_", "_QST_", "_TEST_", "_NoPowers", "_Cache", "_zzOld_"]
                    ):
                        potential_custom_uniques[name_clean] = affix_file_path
                    continue
                with open(affix_file_path, encoding="utf-8") as affix_file:
                    data = json.load(affix_file)
                    desc = data["arStrings"][0]["szText"]
                    desc_clean = remove_content_in_braces(desc.lower().replace("’", ""))
                    num_idx = get_random_number_idx(desc)
                    unique_dict[name_clean] = {"desc": desc_clean, "full": desc, "num_idx": num_idx, "num_inherents": None}
                item_file_name = "_".join(splits[1:])
                item_file_name = item_file_name.replace("stl", "itm")
                item_file_path = d4data_dir / "json" / "base" / "meta" / "Item" / item_file_name
                if not item_file_path.exists():
                    print(f"WARNING: {name_clean} had no item file at {item_file_path}, it will not have an inherents count")
                    continue
                with open(item_file_path, encoding="utf-8") as item_file:
                    data = json.load(item_file)
                    num_inherents = len(data["arInherentAffixes"])
                    unique_dict[name_clean]["num_inherents"] = num_inherents
        # add custom uniques that seem to be missing
        with open(D4LF_BASE_DIR / f"src/tools/data/custom_uniques_{language}.json", encoding="utf-8") as json_file:
            data = json.load(json_file)
            for unique_name, affix_file_path in potential_custom_uniques.items():
                if unique_name not in data:
                    print(
                        f"WARNING: {unique_name} was found in unique files but no affixes were found and no custom unique is created for it. Look for an affix file with a similar name to {affix_file_path}"
                    )
            unique_dict.update(data)
        with open(D4LF_BASE_DIR / f"assets/lang/{language}/uniques.json", "w", encoding="utf-8") as json_file:
            json.dump(unique_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
            json_file.write("\n")

        print(f"Gen Sigils for {language}")
        sigil_dict = {"dungeons": {}, "minor": {}, "major": {}, "positive": {}}

        # Add others automatically
        pattern = f"json/{language}_Text/meta/StringList/world_DGN_*.stl.json"
        json_files = list(d4data_dir.glob(pattern))
        for json_file in json_files:
            with open(json_file, encoding="utf-8") as file:
                data = json.load(file)
                name_idx, _ = (0, 1) if data["arStrings"][0]["szLabel"] == "Name" else (1, 0)
                dungeon_name: str = data["arStrings"][name_idx]["szText"].lower().strip().replace("’", "").replace("'", "")
                sigil_dict["dungeons"][dungeon_name.replace(" ", "_")] = dungeon_name

        pattern = f"json/{language}_Text/meta/StringList/DungeonAffix_*.stl.json"
        json_files = list(d4data_dir.glob(pattern))
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
                            name = name.replace("(", "").replace(")", "").replace("{c_bonus}", "").replace("{/c}", "")
                        else:
                            desc = sigil_affix["szText"].lower().strip().replace("’", "").replace("'", "")
                        sigil_dict[affix_type][name.replace(" ", "_")] = f"{name} {remove_content_in_braces(desc)}"

        # Some of the unique specific affixes are missing. Add them manually
        with open(D4LF_BASE_DIR / f"src/tools/data/custom_sigils_{language}.json", encoding="utf-8") as file:
            data = json.load(file)
            for key, value in data.items():
                if key in sigil_dict:
                    for key2, value2 in value.items():
                        if key2 in sigil_dict[key]:
                            if sigil_dict[key][key2] == value:
                                print(f"Sigil {key2} already exists in sigils.json. Can be deleted from custom json")
                            else:
                                print(f"Sigil {key2} already exists in sigils.json but with different value")
                                sigil_dict[key][key2] = value2
                        else:
                            sigil_dict[key][key2] = value2
                else:
                    sigil_dict[key] = value

        with open(D4LF_BASE_DIR / f"assets/lang/{language}/sigils.json", "w", encoding="utf-8") as json_file:
            json.dump(sigil_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
            json_file.write("\n")

        print(f"Gen Tributes for {language}")
        tribute_dict = {}

        # Add others automatically
        pattern = f"json/{language}_Text/meta/StringList/Item_*_TributeKeySigil_*.stl.json"
        json_files = list(d4data_dir.glob(pattern))
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
        whitelist_types = [
            "Amulet",
            "Axe",
            "Axe2H",
            "Boots",
            "Bow",
            "ChestArmor",
            "Crossbow2H",
            "Dagger",
            "Elixir",
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
            "TemperManual",
            "Tome",
            "Wand",
        ]
        item_typ_dict = {"Material": "custom type material", "Sigil": "custom type sigil", "Incense": "custom type incense"}
        pattern = f"json/{language}_Text/meta/StringList/ItemType_*.stl.json"
        json_files = list(d4data_dir.glob(pattern))
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
                desc = remove_content_in_braces(desc.lower().strip().replace("'", "").replace("’", ""))
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
