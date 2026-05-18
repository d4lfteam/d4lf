# generate data from d4data repo
import json
import re
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

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

SIGIL_AFFIX_TYPES = ("minor", "major", "positive")
SIGIL_RARITY_TAGS = {"white": "Common", "magic": "Magic", "rare": "Rare", "legendary": "Legendary", "mythic": "Mythic"}
D4DATA_REPO = "DiabloTools/d4data"
D4DATA_REF = "master"
GITHUB_USER_AGENT = "d4lf-gen-data"


class D4DataSource:
    def __init__(self, root: Path | None = None):
        self.root = root
        self._paths = None
        self._dir_cache = {}
        self._json_cache = {}

    def glob(self, pattern: str, *, case_sensitive: bool = False):
        pattern = pattern.replace("\\", "/")
        pattern_cmp = pattern if case_sensitive else pattern.lower()
        if self.root is None:
            dir_path, file_pattern = pattern.rsplit("/", 1)
            file_pattern_cmp = file_pattern if case_sensitive else file_pattern.lower()
            return sorted(
                path
                for path in self._list_dir(dir_path)
                if fnmatchcase(PurePosixPath(path if case_sensitive else path.lower()).name, file_pattern_cmp)
            )
        return sorted(
            path for path in self._get_paths() if fnmatchcase(path if case_sensitive else path.lower(), pattern_cmp)
        )

    def exists(self, path: str) -> bool:
        path = self._normalize_path(path)
        if self.root is None:
            dir_path, _ = path.rsplit("/", 1)
            return path in self._list_dir(dir_path)
        return path in self._get_paths()

    def read_json(self, path: str):
        path = self._normalize_path(path)
        if path not in self._json_cache:
            self._json_cache[path] = json.loads(self._read_text(path))
        return self._json_cache[path]

    def read_json_if_exists(self, path: str):
        try:
            return self.read_json(path)
        except FileNotFoundError:
            return None
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise

    def display_path(self, path: str) -> str:
        if self.root is None:
            return f"https://github.com/{D4DATA_REPO}/blob/{D4DATA_REF}/{path}"
        return str(self.root / path)

    def _get_paths(self):
        if self._paths is None:
            self._paths = {path.relative_to(self.root).as_posix() for path in self.root.rglob("*") if path.is_file()}
        return self._paths

    def _list_dir(self, dir_path: str):
        dir_path = self._normalize_path(dir_path)
        if dir_path not in self._dir_cache:
            quoted_path = quote(dir_path, safe="/")
            url = f"https://api.github.com/repos/{D4DATA_REPO}/git/trees/{D4DATA_REF}:{quoted_path}"
            data = json.loads(self._read_url(url))
            self._dir_cache[dir_path] = {
                f"{dir_path}/{item['path']}"
                for item in data["tree"]
                if item["type"] == "blob" and isinstance(item["path"], str)
            }
        return self._dir_cache[dir_path]

    def _read_text(self, path: str) -> str:
        if self.root is not None:
            return (self.root / path).read_text(encoding="utf-8")
        quoted_path = "/".join(quote(part) for part in path.split("/"))
        return self._read_url(f"https://raw.githubusercontent.com/{D4DATA_REPO}/{D4DATA_REF}/{quoted_path}")

    @staticmethod
    def _read_url(url: str) -> str:
        request = Request(url, headers={"User-Agent": GITHUB_USER_AGENT})  # noqa: S310
        with urlopen(request, timeout=60) as response:  # noqa: S310
            return response.read().decode("utf-8")

    @staticmethod
    def _normalize_path(path: str) -> str:
        return path.replace("\\", "/")


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


def get_string_list_dir(language: str) -> str:
    return f"json/{language}_Text/meta/StringList"


def get_string_list_path(language: str, file_name: str) -> str:
    return f"{get_string_list_dir(language)}/{file_name}"


def clean_sigil_text(text: str) -> str:
    cleaned = text.lower().strip().replace("\u2019", "").replace("'", "")
    cleaned = cleaned.replace("(", "").replace(")", "")
    return remove_content_in_braces(cleaned)


def get_sigil_rarity(text: str) -> str | None:
    for tag, rarity in SIGIL_RARITY_TAGS.items():
        if f"{{c_{tag}}}" in text:
            return rarity
    return None


def main(d4data_source: D4DataSource, companion_app_dir: Path | None = None):
    lang_arr = [
        "enUS"
    ]  # "deDE", "frFR", "esES", "esMX", "itIT", "jaJP", "koKR", "plPL", "ptBR", "ruRU", "trTR", "zhCN", "zhTW"]

    existing_affixes = {}
    for lang in lang_arr:
        affixes_file = D4LF_BASE_DIR / f"assets/lang/{lang}/affixes.json"
        if affixes_file.exists():
            with affixes_file.open(encoding="utf-8") as file:
                existing_affixes[lang] = json.load(file)

    for lang in lang_arr:
        Path(f"assets/lang/{lang}").mkdir(exist_ok=True, parents=True)

    for language in lang_arr:
        # Create Aspects
        generate_aspects(d4data_source, language)

        # Create Uniques
        generate_uniques(d4data_source, language)

        # Create Sigils
        generate_sigils(d4data_source, language)

        print(f"Gen Tributes for {language}")
        tribute_dict = {}

        # Add others automatically
        pattern = "Item_*_TributeKeySigil_*.stl.json"
        json_files = d4data_source.glob(f"{get_string_list_dir(language)}/{pattern}", case_sensitive=False)
        for json_file in json_files:
            data = d4data_source.read_json(json_file)
            name_idx, _ = (0, 1) if data["arStrings"][0]["szLabel"] == "Name" else (1, 0)
            tribute_name: str = (
                data["arStrings"][name_idx]["szText"].lower().strip().replace("\u2019", "").replace("'", "")
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
        pattern = "ItemType_*.stl.json"
        json_files = d4data_source.glob(f"{get_string_list_dir(language)}/{pattern}", case_sensitive=False)
        for json_file in json_files:
            item_type = PurePosixPath(json_file).stem.split("_")[1].split(".")[0].strip()
            data = d4data_source.read_json(json_file)
            name_idx = 0 if data["arStrings"][0]["szLabel"] == "Name" else 1
            name_str: str = check_ms(data["arStrings"][name_idx]["szText"]).lower().strip()
            if item_type in whitelist_types:
                item_typ_dict[item_type] = name_str
        with Path(D4LF_BASE_DIR / f"assets/lang/{language}/item_types.json").open("w", encoding="utf-8") as json_file:
            json.dump(item_typ_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
            json_file.write("\n")

        print(f"Gen Tooltips for {language}")
        tooltip_dict = {}
        data = d4data_source.read_json(get_string_list_path(language, "UIToolTips.stl.json"))
        for arString in data["arStrings"]:
            if arString["szLabel"] == "ItemPower":
                tooltip_dict["ItemPower"] = remove_content_in_braces(check_ms(arString["szText"].lower()))
        with Path(D4LF_BASE_DIR / f"assets/lang/{language}/tooltips.json").open("w", encoding="utf-8") as json_file:
            json.dump(tooltip_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
            json_file.write("\n")

        # Create Affixes
        generate_affixes(language, existing_affixes.get(language, {}), companion_app_dir)

        print("=============================")


def get_companion_affixes_path(companion_app_dir: Path, language: str) -> Path:
    candidates = [
        companion_app_dir / f"D4Companion/Data/Affixes.{language}.json",
        companion_app_dir / f"Data/Affixes.{language}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    msg = f"Could not find Affixes.{language}.json under {companion_app_dir}"
    raise FileNotFoundError(msg)


def add_custom_affixes(affix_dict, language):
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


def generate_affixes(language, existing_affixes, companion_app_dir):
    print(f"Gen Affixes for {language}")
    affix_dict = existing_affixes.copy()
    if companion_app_dir is not None:
        affix_dict = {}
        with get_companion_affixes_path(companion_app_dir, language).open(encoding="utf-8") as file:
            data = json.load(file)
            for affix in data:
                desc: str = affix["Description"]
                desc = desc.lower().strip().replace("'", "").replace("\u2019", "").replace(".", "")
                desc = remove_content_in_braces(desc)
                desc = desc.removeprefix("x ")
                name = desc.replace(",", "").replace(" ", "_")
                if len(desc) > 2:
                    affix_dict[name] = desc
        add_custom_affixes(affix_dict, language)
    elif not affix_dict:
        print(f"WARNING: No companion app path provided and no existing affixes.json found for {language}.")

    with Path(D4LF_BASE_DIR / f"assets/lang/{language}/affixes.json").open("w", encoding="utf-8") as json_file:
        json.dump(affix_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")


def add_custom_sigils(sigil_dict, language):
    with Path(D4LF_BASE_DIR / f"src/tools/data/custom_sigils_{language}.json").open(encoding="utf-8") as file:
        data = json.load(file)
        for key, values in data.items():
            if key in sigil_dict:
                for key2, value2 in values.items():
                    custom_value = get_custom_sigil_value(key, value2)
                    if key2 in sigil_dict[key]:
                        if sigil_dict[key][key2] == custom_value:
                            print(f"Sigil {key2} already exists in sigils.json. Can be deleted from custom json")
                        else:
                            print(f"Sigil {key2} already exists in sigils.json but with different value")
                            sigil_dict[key][key2] = custom_value
                    else:
                        sigil_dict[key][key2] = custom_value
            else:
                sigil_dict[key] = values


def get_sigil_affix_value(text: str, rarity: str | None = None):
    value = {"text": text}
    if rarity:
        value["rarity"] = rarity
    return value


def get_custom_sigil_value(sigil_type: str, value):
    if sigil_type in SIGIL_AFFIX_TYPES and isinstance(value, str):
        return get_sigil_affix_value(value)
    return value


def add_sigil_dungeons(d4data_source, language, sigil_dict):
    world_pattern = "json/base/meta/World/DGN_*.wrl.json"
    world_files = d4data_source.glob(world_pattern, case_sensitive=False)
    for world_file in world_files:
        world_name = PurePosixPath(world_file).name.removesuffix(".wrl.json")
        string_world_file = get_string_list_path(language, f"World_{world_name}.stl.json")
        data = d4data_source.read_json_if_exists(string_world_file)
        if data is None:
            print(f"WARNING: Could not find file named {d4data_source.display_path(string_world_file)} in d4data.")
            continue

        name_items = [item for item in data["arStrings"] if item["szLabel"] == "Name"]
        if not name_items:
            continue
        dungeon_name: str = clean_sigil_text(name_items[0]["szText"])
        sigil_dict["dungeons"][dungeon_name.replace(" ", "_")] = dungeon_name


def add_sigil_affixes(d4data_source, language, sigil_dict):
    affix_pattern = "json/base/meta/DungeonAffix/*.dax.json"
    affix_files = d4data_source.glob(affix_pattern, case_sensitive=False)
    for affix_file in affix_files:
        affix_file_name = PurePosixPath(affix_file).name.removesuffix(".dax.json")
        affix_type = affix_file_name.split("_", 1)[0].lower().strip()
        if affix_type not in SIGIL_AFFIX_TYPES:
            continue

        string_affix_file = get_string_list_path(language, f"DungeonAffix_{affix_file_name}.stl.json")
        data = d4data_source.read_json_if_exists(string_affix_file)
        if data is None:
            print(f"WARNING: Could not find file named {d4data_source.display_path(string_affix_file)} in d4data.")
            continue

        name = ""
        desc = ""
        rarity = None
        for sigil_affix in data["arStrings"]:
            text = sigil_affix["szText"]
            rarity = rarity or get_sigil_rarity(text)
            if sigil_affix["szLabel"] == "AffixName":
                name = clean_sigil_text(text)
            else:
                desc = clean_sigil_text(text)

        if not name:
            continue
        sigil_key = name.replace(" ", "_")
        sigil_dict[affix_type][sigil_key] = get_sigil_affix_value(f"{name} {desc}".strip(), rarity)


def generate_sigils(d4data_source, language):
    print(f"Gen Sigils for {language}")
    sigil_dict = {"dungeons": {}, "minor": {}, "major": {}, "positive": {}}

    add_sigil_dungeons(d4data_source, language, sigil_dict)
    add_sigil_affixes(d4data_source, language, sigil_dict)
    add_custom_sigils(sigil_dict, language)

    with Path(D4LF_BASE_DIR / f"assets/lang/{language}/sigils.json").open("w", encoding="utf-8") as json_file:
        json.dump(sigil_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")


def generate_aspects(d4data_source, language):
    print(f"Gen Aspects for {language}")
    aspects_list = []
    aspect_pattern = "json/base/meta/Aspect/*.json"
    aspect_files = d4data_source.glob(aspect_pattern, case_sensitive=False)

    for core_aspect_file in aspect_files:
        if PurePosixPath(core_aspect_file).name.endswith("Axe Bad Data.asp.json"):
            continue
        # Get the associated Aspect file, which will tell us where to find the aspect file
        aspect_data = d4data_source.read_json(core_aspect_file)
        affix_name = aspect_data["snoAffix"]["name"]

        core_affix_file_name = f"Affix_{affix_name}.stl.json"
        core_affix_file = get_string_list_path(language, core_affix_file_name)
        data = d4data_source.read_json_if_exists(core_affix_file)
        if data is None:
            print(f"WARNING: Could not find file named {d4data_source.display_path(core_affix_file)} in d4data.")
            continue

        name_idx = 0 if data["arStrings"][0]["szLabel"] == "Name" else 1
        aspect_name = data["arStrings"][name_idx]["szText"]
        aspect_name_clean = aspect_name.strip().replace(" ", "_").lower().replace("\u2019", "").replace("'", "")
        aspect_name_clean = check_ms(aspect_name_clean)
        if is_placeholder_or_test_name(aspect_name_clean):
            continue
        aspects_list.append(aspect_name_clean)

    with Path(D4LF_BASE_DIR / f"assets/lang/{language}/aspects.json").open("w", encoding="utf-8") as json_file:
        aspects_list.sort()
        json.dump(aspects_list, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")


def generate_uniques(d4data_source, language):
    items_to_ignore = ["halo", "pact_amulet", "wilted_potential"]

    print(f"Gen Uniques for {language}")
    unique_dict = {}
    unique_pattern = "json/base/meta/Item/*nique*.itm.json"
    unique_files = d4data_source.glob(unique_pattern, case_sensitive=False)

    for core_unique_file in unique_files:
        if PurePosixPath(core_unique_file).name.startswith("S10_"):
            # Chaos uniques really throw off our inherent counts
            continue
        # Get inherent count and item type from this file. Beyond that, we need the file name to find the enUS strings file.
        num_inherents = 0
        unique_item_data = d4data_source.read_json(core_unique_file)
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
            affix_file = f"json/{affix_file_path}.json"
            affix_data = d4data_source.read_json(affix_file)
            num_inherents += len(affix_data["ptItemAffixAttributes"])

        core_unique_file_id = PurePosixPath(core_unique_file).name.split(".")[0]
        string_item_file_name = f"Item_{core_unique_file_id}.stl.json"
        string_item_file = get_string_list_path(language, string_item_file_name)

        data = d4data_source.read_json_if_exists(string_item_file)
        if data is None:
            print(f"WARNING: Could not find file named {d4data_source.display_path(string_item_file)} in d4data.")
            continue

        name_item = [item for item in data["arStrings"] if item["szLabel"] == "Name"]
        if not name_item:
            continue
        name = name_item[0]["szText"]
        name_clean = (
            name
            .strip()
            .replace(" ", "_")
            .replace("\xa0", "_")
            .lower()
            .replace("\u2019", "")
            .replace("'", "")
            .replace(",", "")
        )
        name_clean = check_ms(name_clean)
        if name_clean in items_to_ignore or is_placeholder_or_test_name(name_clean):
            continue

        unique_dict[name_clean] = {"num_inherents": num_inherents}

    with Path(D4LF_BASE_DIR / f"assets/lang/{language}/uniques.json").open("w", encoding="utf-8") as json_file:
        json.dump(unique_dict, json_file, indent=4, ensure_ascii=False, sort_keys=True)
        json_file.write("\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Path Argument Parser")
    parser.add_argument(
        "d4data_dir", nargs="?", type=str, help="Optional path to d4data repo. Omit to read d4data online from GitHub."
    )  # https://github.com/DiabloTools/d4data.git
    parser.add_argument(
        "companion_app_dir",
        nargs="?",
        type=str,
        help="Optional path to Diablo4Companion. Required to regenerate affixes.json.",
    )
    args = parser.parse_args()

    input_path = Path(args.d4data_dir) if args.d4data_dir else None
    companion_path = Path(args.companion_app_dir) if args.companion_app_dir else None

    if companion_path is not None and not companion_path.is_dir():
        print(f"The provided companion app path '{companion_path}' does not exist or is not a directory.")
    elif input_path is None:
        main(D4DataSource(), companion_path)
    elif input_path.exists() and input_path.is_dir():
        main(D4DataSource(input_path), companion_path)
    else:
        print(f"The provided path '{input_path}' does not exist or is not a directory.")
