"""Generation of aspects, sigils, uniques, sets, and the complete dataset."""

from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, cast

from src.tools.data_generation.affixes import generate_affixes, get_string_list_name, merge_custom_data
from src.tools.data_generation.common import (
    D4LF_BASE_DIR,
    check_ms,
    clean_item_name,
    is_placeholder_or_test_name,
    load_json_file,
    remove_content_in_braces,
    write_json_file,
)
from src.tools.data_generation.constants import GEAR_TYPES, SIGIL_RARITY_COLOR_TAGS

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.type_aliases import JsonObject, JsonValue


def _run_stage(name: str, function: Callable[..., int], *args: JsonValue | Path, **kwargs: JsonValue | Path) -> int:
    print(f"START {name}")
    started = perf_counter()
    count = function(*args, **kwargs) or 0
    print(f"FINISH {name}: {count} files, elapsed={perf_counter() - started:.3f}s")
    return count


def main(d4data_dir: Path) -> None:
    lang_arr = ["enUS"]  # "deDE", "frFR", "esES", "esMX", "itIT", "jaJP", "koKR", "plPL", "ptBR", "ruFR"

    for lang in lang_arr:
        for name in (
            "affixes",
            "seals_affixes",
            "charms_affixes",
            "aspects",
            "sets",
            "uniques",
            "sigils",
            "tributes",
            "item_types",
            "tooltips",
        ):
            Path(f"assets/lang/{lang}/{name}.json").unlink(missing_ok=True)
        Path(f"assets/lang/{lang}").mkdir(exist_ok=True, parents=True)

    for language in lang_arr:
        _run_stage("aspects", generate_aspects, d4data_dir, language)
        _run_stage("uniques", generate_uniques, d4data_dir, language)
        _run_stage("sets", generate_sets, d4data_dir, language)
        _run_stage("sigils", generate_sigils, d4data_dir, language)

        print(f"START tributes for {language}")
        started = perf_counter()
        tribute_dict = {}

        pattern = f"json/{language}_Text/meta/StringList/Item_*_TributeKeySigil_*.stl.json"
        json_files = sorted(d4data_dir.glob(pattern, case_sensitive=False))
        for json_file in json_files:
            data = cast("dict[str, list[dict[str, str]]]", load_json_file(json_file))
            name_idx = 0 if data["arStrings"][0]["szLabel"] == "Name" else 1
            tribute_name = data["arStrings"][name_idx]["szText"].lower().strip().replace("’", "").replace("'", "")  # ruff:ignore[RUF001]
            tribute_dict[tribute_name.replace(" ", "_").replace("(", "").replace(")", "")] = tribute_name

        merge_custom_data(tribute_dict, "tributes", language)
        write_json_file(D4LF_BASE_DIR / f"assets/lang/{language}/tributes.json", tribute_dict)
        print(f"FINISH tributes: {len(json_files)} files, elapsed={perf_counter() - started:.3f}s")

        print(f"START item_types for {language}")
        started = perf_counter()
        whitelist_types = [*GEAR_TYPES, "Elixir", "TemperManual", "Tome"]
        item_typ_dict = {
            "Material": "custom type material",
            "Sigil": "custom type sigil",
            "Incense": "custom type incense",
        }
        pattern = f"json/{language}_Text/meta/StringList/ItemType_*.stl.json"
        json_files = sorted(d4data_dir.glob(pattern, case_sensitive=False))
        for json_file in json_files:
            item_type = json_file.stem.split("_")[1].split(".")[0].strip()
            data = cast("dict[str, list[dict[str, str]]]", load_json_file(json_file))
            name_idx = 0 if data["arStrings"][0]["szLabel"] == "Name" else 1
            name_str = check_ms(data["arStrings"][name_idx]["szText"]).lower().strip()
            if item_type in whitelist_types:
                item_typ_dict[item_type] = {"Axe": "axe", "Sword": "sword"}.get(item_type, name_str)
        merge_custom_data(item_typ_dict, "item_types", language)
        write_json_file(D4LF_BASE_DIR / f"assets/lang/{language}/item_types.json", item_typ_dict)
        print(f"FINISH item_types: {len(json_files)} files, elapsed={perf_counter() - started:.3f}s")

        print(f"START tooltips for {language}")
        started = perf_counter()
        tooltip_dict = {}
        tooltip_file = d4data_dir / f"json/{language}_Text/meta/StringList/UIToolTips.stl.json"
        for ar_string in cast("dict[str, list[dict[str, str]]]", load_json_file(tooltip_file))["arStrings"]:
            if ar_string["szLabel"] == "ItemPower":
                tooltip_dict["ItemPower"] = remove_content_in_braces(check_ms(ar_string["szText"].lower()))
        merge_custom_data(tooltip_dict, "tooltips", language)
        write_json_file(D4LF_BASE_DIR / f"assets/lang/{language}/tooltips.json", tooltip_dict)
        print(f"FINISH tooltips: 1 files, elapsed={perf_counter() - started:.3f}s")

        _run_stage("affixes", generate_affixes, d4data_dir, language)

        print("=============================")


def generate_aspects(d4data_dir: Path, language: str) -> int:
    print(f"Gen Aspects for {language}")
    aspects_list = []
    aspect_pattern = "json/base/meta/Aspect/*.json"
    aspect_files = sorted(d4data_dir.glob(aspect_pattern, case_sensitive=False))

    for core_aspect_file in aspect_files:
        if core_aspect_file.name.endswith("Axe Bad Data.asp.json"):
            continue
        affix_name = cast("dict[str, dict[str, str]]", load_json_file(core_aspect_file))["snoAffix"]["name"]
        core_affix_file = d4data_dir / f"json/{language}_Text/meta/StringList/Affix_{affix_name}.stl.json"
        if not core_affix_file.exists():
            print(f"WARNING: Could not find file named {core_affix_file} in d4data.")
        aspect_name_clean = get_string_list_name(core_affix_file)
        if aspect_name_clean is None or is_placeholder_or_test_name(aspect_name_clean):
            continue
        aspects_list.append(aspect_name_clean)

    merge_custom_data(aspects_list, "aspects", language)
    aspects_list.sort()
    write_json_file(D4LF_BASE_DIR / f"assets/lang/{language}/aspects.json", aspects_list)
    return len(aspect_files)


def generate_sigils(d4data_dir: Path, language: str) -> int:
    print(f"Gen Sigils for {language}")
    sigil_dict = {"dungeons": {}, "minor": {}, "major": {}, "positive": {}}
    sigil_rarity_dict = {}
    string_list_dir = d4data_dir / f"json/{language}_Text/meta/StringList"
    source_file_count = 0

    pattern = "json/base/meta/World/DGN_*.wrl.json"
    json_files = sorted(d4data_dir.glob(pattern, case_sensitive=False))
    source_file_count += len(json_files)
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
    source_file_count += len(json_files)
    for json_file in json_files:
        dungeon_affix_file_id = json_file.name.removesuffix(".dax.json")
        affix_type = dungeon_affix_file_id.split("_", maxsplit=1)[0].lower().strip()
        if affix_type not in sigil_dict or affix_type == "dungeons":
            continue

        string_list_file = string_list_dir / f"DungeonAffix_{dungeon_affix_file_id}.stl.json"
        if not string_list_file.exists():
            print(f"WARNING: Could not find string list for dungeon affix {json_file}.")
            continue

        data = cast("JsonObject", load_json_file(string_list_file))
        raw_name = string_list_value(data, "AffixName")
        rarity = None
        for color_tag, sigil_rarity in SIGIL_RARITY_COLOR_TAGS.items():
            if f"{{{color_tag}}}" in raw_name:
                rarity = sigil_rarity
                break
        name = remove_content_in_braces(raw_name).replace("(", "").replace(")", "")
        desc = string_list_value(data, "AffixDesc").lower().strip().replace("’", "").replace("'", "")  # ruff:ignore[RUF001]
        desc = remove_content_in_braces(desc)
        sigil_name_key = clean_item_name(name)
        sigil_dict[affix_type][sigil_name_key] = f"{sigil_name_key.replace('_', ' ')} {desc}"
        if rarity is not None:
            sigil_rarity_dict[sigil_name_key] = rarity

    merge_custom_data(sigil_dict, "sigils", language)

    sigil_dict["rarities"] = sigil_rarity_dict

    write_json_file(D4LF_BASE_DIR / f"assets/lang/{language}/sigils.json", sigil_dict)
    return source_file_count


def string_list_value(data: JsonObject, label: str) -> str:
    entries = cast("list[dict[str, str]]", data.get("arStrings", []))
    for entry in entries:
        if entry["szLabel"] == label:
            return entry["szText"]
    return ""


def generate_uniques(d4data_dir: Path, language: str) -> int:
    items_to_ignore = ["halo", "pact_amulet", "wilted_potential", "mythic_unique_horadric_seal"]
    print(f"Gen Uniques for {language}")
    unique_dict: dict[str, dict[str, int]] = {}
    unique_files = sorted(
        set(d4data_dir.glob("json/base/meta/Item/*nique*.itm.json", case_sensitive=False))
        | set(d4data_dir.glob("json/base/meta/Item/Runeword_*.itm.json", case_sensitive=False))
    )

    for core_unique_file in unique_files:
        if core_unique_file.name.startswith("S10_"):
            continue
        num_inherents = 0
        unique_item_data = cast("dict[str, dict[str, str] | list[dict[str, str]]]", load_json_file(core_unique_file))
        item_type = cast("dict[str, str]", unique_item_data.get("snoItemType") or {}).get("name", "")
        if item_type not in ("HoradricSeal", "Charm", "Seal") and not bool(unique_item_data.get("arForcedAffixes")):
            continue
        inherent_affixes = cast("list[dict[str, str]]", unique_item_data.get("arInherentAffixes", []))
        base_item_type = item_type.split("_", maxsplit=1)[0]
        if base_item_type not in GEAR_TYPES and item_type not in ("FocusBookOffHand", "HoradricSeal", "Charm", "Seal"):
            continue
        core_unique_file_id = core_unique_file.name.split(".")[0]
        string_item_file = d4data_dir / f"json/{language}_Text/meta/StringList/Item_{core_unique_file_id}.stl.json"
        if not string_item_file.exists():
            print(f"WARNING: Could not find file named {string_item_file} in d4data.")
            continue
        name_clean = get_string_list_name(string_item_file)
        if name_clean is None or name_clean in items_to_ignore or is_placeholder_or_test_name(name_clean):
            continue
        for inherent_affix in inherent_affixes:
            if inherent_affix["name"].startswith("UNIQUE_INHERENT_Evade_MovementSpeed_"):
                num_inherents += 1
                continue
            affix_file = d4data_dir / f"json/{inherent_affix['__targetFileName__']}.json"
            num_inherents += len(
                cast("dict[str, list[JsonValue]]", load_json_file(affix_file))["ptItemAffixAttributes"]
            )
        existing_num_inherents = unique_dict.get(name_clean, {}).get("num_inherents", 0)
        unique_dict[name_clean] = {"num_inherents": max(num_inherents, existing_num_inherents)}

    merge_custom_data(unique_dict, "uniques", language)
    write_json_file(D4LF_BASE_DIR / f"assets/lang/{language}/uniques.json", unique_dict)
    return len(unique_files)


def generate_sets(d4data_dir: Path, language: str) -> int:
    print(f"Gen Sets for {language}")
    sets_list = []
    charm_pattern = "json/base/meta/Item/Talisman_Charm*.itm.json"
    charm_files = sorted(d4data_dir.glob(charm_pattern, case_sensitive=False))

    for charm_file in charm_files:
        charm_data = cast("dict[str, dict[str, str]]", load_json_file(charm_file))
        if charm_data["snoItemType"]["name"] != "Charm":
            continue
        set_item_bonus = charm_data.get("snoSetItemBonus")
        if not bool(set_item_bonus):
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
    merge_custom_data(sets_list, "sets", language)
    sets_list.sort()
    write_json_file(D4LF_BASE_DIR / f"assets/lang/{language}/sets.json", sets_list)
    return len(charm_files)
