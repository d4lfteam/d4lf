import json
import logging
import re
from dataclasses import dataclass

import lxml.html

import src.logger
from src.config.models import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    ItemFilterModel,
    ProfileModel,
    UniqueModel,
)
from src.dataloader import Dataloader
from src.gui.importer.common import (
    add_to_profiles,
    get_class_name,
    get_with_retry,
    match_to_enum,
    retry_importer,
    save_as_profile,
    update_mingreateraffixcount,
)
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.paragon_export import build_paragon_profile_payload, extract_maxroll_paragon_steps
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType
from src.item.descr.text import clean_str, closest_match
from src.scripts import correct_name

LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True
BUILD_GUIDE_BASE_URL = "https://maxroll.gg/d4/build-guides/"
BUILD_GUIDE_PLANNER_EMBED_XPATH = "//*[contains(@class, 'd4-embed')]"
PLANNER_API_BASE_URL = "https://planners.maxroll.gg/profiles/d4/"
PLANNER_API_DATA_URL = "https://assets-ng.maxroll.gg/d4-tools/game/data.min.json?7659ec67"
PLANNER_BASE_URL = "https://maxroll.gg/d4/planner/"
_NON_BUILD_VARIANT_NAMES = {"skill tree", "skills", "skills only", "skill tree only"}
_LOGGED_UNSUPPORTED_AFFIX_ATTRIBUTES: set[str] = set()


class MaxrollException(Exception):
    """Raised when Maxroll content cannot be parsed."""


@dataclass(slots=True)
class MaxrollVariantOption:
    """Represents one importable Maxroll planner variant."""

    index: int
    label: str


@retry_importer
def import_maxroll(config: ImportConfig):
    """Import one or more Maxroll variants into d4lf profiles."""
    url = config.url.strip().replace("\n", "")
    if PLANNER_BASE_URL not in url and BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a maxroll build guide or maxroll planner url")
        return
    LOGGER.info(f"Loading {url}")
    api_url, build_id = (
        _extract_planner_url_and_id_from_guide(url)
        if BUILD_GUIDE_BASE_URL in url
        else _extract_planner_url_and_id_from_planner(url)
    )
    try:
        response = get_with_retry(url=api_url)
    except ConnectionError:
        LOGGER.error("Couldn't get planner")
        return
    all_data = response.json()
    build_data = json.loads(all_data["data"])
    items = build_data["items"]
    try:
        mapping_data = get_with_retry(url=PLANNER_API_DATA_URL).json()
    except ConnectionError:
        LOGGER.error("Couldn't get planner data")
        return

    profile_indices = _resolve_profile_indices(
        url=url,
        build_data=build_data,
        selected_profile_index=build_id,
        selected_profile_indices=config.selected_profile_indices,
    )
    created_profiles: list[str] = []
    for profile_index in profile_indices:
        active_profile = build_data["profiles"][profile_index]
        if not active_profile.get("items"):
            LOGGER.warning(f"Skipping empty Maxroll planner profile {profile_index + 1}")
            continue

        profile = _build_profile(active_profile=active_profile, items=items, mapping_data=mapping_data, config=config)
        build_name = _resolve_output_file_name(
            config=config,
            all_data=all_data,
            active_profile=active_profile,
            build_id=profile_index,
            import_count=len(profile_indices),
        )

        paragon_step_count = 0
        if config.export_paragon:
            steps = extract_maxroll_paragon_steps(active_profile)
            if steps:
                paragon_step_count = len(steps)
                profile.Paragon = build_paragon_profile_payload(
                    build_name=build_name, source_url=url, paragon_boards_list=steps
                )
            else:
                LOGGER.warning("Paragon export enabled, but no paragon steps were found in this Maxroll profile.")

        corrected_file_name = save_as_profile(file_name=build_name, profile=profile, url=url)
        if paragon_step_count:
            LOGGER.info(
                f"Paragon imported successfully for {corrected_file_name} with {paragon_step_count} board step(s)."
            )
        created_profiles.append(corrected_file_name)

        if config.add_to_profiles:
            add_to_profiles(corrected_file_name)

    if created_profiles:
        LOGGER.info(f"Finished importing {len(created_profiles)} Maxroll profile(s)")
    else:
        LOGGER.warning("No Maxroll profiles were imported")


def get_maxroll_variant_options(url: str) -> list[MaxrollVariantOption]:
    """Return importable Maxroll planner variants for a Maxroll guide or planner URL."""
    normalized_url = url.strip().replace("\n", "")
    if PLANNER_BASE_URL not in normalized_url and BUILD_GUIDE_BASE_URL not in normalized_url:
        LOGGER.error("Invalid url, please use a maxroll build guide or maxroll planner url")
        return []

    api_url, selected_profile_index = (
        _extract_planner_url_and_id_from_guide(normalized_url)
        if BUILD_GUIDE_BASE_URL in normalized_url
        else _extract_planner_url_and_id_from_planner(normalized_url)
    )
    try:
        response = get_with_retry(url=api_url)
    except ConnectionError:
        LOGGER.error("Couldn't get planner")
        return []

    all_data = response.json()
    build_data = json.loads(all_data["data"])
    profiles = build_data.get("profiles", [])
    if not profiles:
        return [MaxrollVariantOption(index=selected_profile_index, label=f"Profile {selected_profile_index + 1}")]

    return [
        MaxrollVariantOption(index=index, label=str(profile.get("name", "")).strip() or f"Profile {index + 1}")
        for index, profile in enumerate(profiles)
        if _should_import_profile_variant(profile)
    ]


def _resolve_profile_indices(
    url: str, build_data: dict, selected_profile_index: int, selected_profile_indices: list[int] | None = None
) -> list[int]:
    """Resolve which Maxroll profile indices should be imported."""
    profiles = build_data.get("profiles", [])
    if not profiles:
        return [selected_profile_index]
    if BUILD_GUIDE_BASE_URL not in url:
        return [selected_profile_index]

    importable_indices: list[int] = []
    skipped_profile_names: list[str] = []
    for index, profile in enumerate(profiles):
        if _should_import_profile_variant(profile):
            importable_indices.append(index)
            continue
        skipped_profile_names.append(str(profile.get("name", "")).strip() or f"profile_{index + 1}")

    if len(profiles) > 1:
        LOGGER.info(f"Found {len(profiles)} Maxroll planner variants.")
    for skipped_profile_name in skipped_profile_names:
        LOGGER.info(f"Skipping non-build Maxroll planner variant '{skipped_profile_name}'.")

    if selected_profile_indices is not None:
        filtered_selected_profile_indices = [index for index in selected_profile_indices if index in importable_indices]
        LOGGER.info(f"Importing {len(filtered_selected_profile_indices)} selected Maxroll planner variant(s).")
        return filtered_selected_profile_indices

    if len(importable_indices) > 1:
        LOGGER.info("Importing all variants.")

    return importable_indices or [selected_profile_index]


def _should_import_profile_variant(profile: dict) -> bool:
    """Return whether a Maxroll profile variant should be treated as a build."""
    variant_name = str(profile.get("name", "")).strip().casefold()
    return variant_name not in _NON_BUILD_VARIANT_NAMES


def _resolve_output_file_name(
    config: ImportConfig, all_data: dict, active_profile: dict, build_id: int, import_count: int
) -> str:
    """Resolve the output profile filename for an imported Maxroll build."""
    if not config.custom_file_name:
        return _build_default_file_name(all_data=all_data, active_profile=active_profile, build_id=build_id)

    if import_count <= 1:
        return config.custom_file_name

    variant_name = str(active_profile.get("name", "")).strip() or f"profile_{build_id + 1}"
    return f"{config.custom_file_name}_{variant_name}"


def _build_profile(active_profile: dict, items: dict, mapping_data: dict, config: ImportConfig) -> ProfileModel:
    """Build a d4lf profile model from a Maxroll profile payload."""
    finished_filters = []
    unique_filters = []
    aspect_upgrade_filters = []
    for item_id in active_profile["items"].values():
        resolved_item = items[str(item_id)]
        resolved_item_id = resolved_item["id"]

        if (
            resolved_item_id in mapping_data["items"]
            and mapping_data["items"][resolved_item_id]["magicType"] in [2, 4]
            and config.import_uniques
        ):
            unique_model = UniqueModel()
            unique_name = mapping_data["items"][resolved_item_id]["name"]
            try:
                unique_name = _unique_name_special_handling(unique_name)
                unique_model.aspect = AspectUniqueFilterModel(name=unique_name)
                unique_filters.append(unique_model)
            except Exception:
                LOGGER.exception(f"Unexpected error importing unique {unique_name}, please report a bug.")
            continue

        item_filter = ItemFilterModel()
        if (item_type := _find_item_type(mapping_data=mapping_data["items"], value=resolved_item["id"])) is None:
            LOGGER.warning(
                f"Couldn't find item type for {resolved_item['id']} from mapping data provided by Maxroll. Skipping item."
            )
            continue
        item_filter.itemType = [item_type]

        if (
            resolved_item["id"] in mapping_data["items"]
            and mapping_data["items"][resolved_item["id"]]["magicType"] == 1
            and config.import_aspect_upgrades
        ):
            legendary_aspect = _find_legendary_aspect(
                mapping_data=mapping_data,
                legendary_aspect=_extract_legendary_aspect_payload(
                    resolved_item=resolved_item, mapping_item=mapping_data["items"].get(resolved_item["id"])
                ),
            ) or _find_legendary_aspect_from_explicit_affixes(
                mapping_data=mapping_data, item_explicit_affixes=resolved_item.get("explicits", [])
            )
            if legendary_aspect:
                if legendary_aspect not in Dataloader().aspect_list:
                    LOGGER.warning(
                        f"Found legendary aspect '{legendary_aspect}' that is not in our aspect data, unable to add "
                        f"to AspectUpgrades. Please report a bug."
                    )
                else:
                    aspect_upgrade_filters.append(legendary_aspect)
            else:
                msg = (
                    f"Unable to find legendary aspect in maxroll data for {item_type}, can not automatically add "
                    f"to AspectUpgrades."
                )
                if len(resolved_item["explicits"]) == 3:
                    msg += (
                        " We suspect this item is actually a rare and maxroll is falsely reporting it as a legendary, "
                        "please double check."
                    )
                    LOGGER.debug(msg)
                else:
                    LOGGER.warning(msg)

        item_filter.affixPool = [
            AffixFilterCountModel(
                count=[
                    AffixFilterModel(name=affix.name, want_greater=affix.type == AffixType.greater)
                    for affix in _find_item_affixes(
                        mapping_data=mapping_data,
                        item_affixes=resolved_item["explicits"],
                        import_greater_affixes=config.import_greater_affixes,
                    )
                ],
                minCount=3,
            )
        ]
        item_filter.minPower = 100
        update_mingreateraffixcount(item_filter, config.require_greater_affixes)

        if "implicits" in resolved_item and item_type in [ItemType.Boots]:
            item_filter.inherentPool = [
                AffixFilterCountModel(
                    count=[
                        AffixFilterModel(name=affix.name)
                        for affix in _find_item_affixes(
                            mapping_data=mapping_data, item_affixes=resolved_item["implicits"]
                        )
                    ]
                )
            ]

        filter_name = item_filter.itemType[0].name
        suffix = 2
        while any(filter_name == next(iter(existing_filter)) for existing_filter in finished_filters):
            filter_name = f"{item_filter.itemType[0].name}{suffix}"
            suffix += 1

        finished_filters.append({filter_name: item_filter})

    profile = ProfileModel(name="imported profile", Affixes=sorted(finished_filters, key=lambda item: next(iter(item))))
    if config.import_uniques and unique_filters:
        profile.Uniques = unique_filters
    if config.import_aspect_upgrades and aspect_upgrade_filters:
        profile.AspectUpgrades = aspect_upgrade_filters
    return profile


def _build_default_file_name(all_data: dict, active_profile: dict, build_id: int) -> str:
    """Build the default d4lf profile filename for a Maxroll import."""
    class_name = get_class_name(str(all_data.get("class", "")))
    build_name = str(all_data.get("name", "")).strip() or class_name
    variant_name = str(active_profile.get("name", "")).strip()

    file_name_parts = ["maxroll"]
    if class_name and class_name != "Unknown":
        file_name_parts.append(class_name)
    if build_name:
        file_name_parts.append(build_name)
    if variant_name:
        file_name_parts.append(variant_name)
    elif active_profile.get("items"):
        file_name_parts.append(f"profile_{build_id + 1}")

    return "_".join(part for part in file_name_parts if part)


def _corrections(input_str: str) -> str:
    """Normalize known Maxroll attribute description identifiers."""
    match input_str:
        case "On_Hit_Vulnerable_Proc_Chance":
            return "On_Hit_Vulnerable_Proc"
        case "Movement_Bonus_On_Elite_Kill":
            return "Movement_Speed_Bonus_On_Elite_Kill"
    return input_str


def _tokenize_identifier(value: object) -> list[str]:
    """Split a Maxroll identifier into lowercase tokens."""
    parts = re.findall(r"[A-Z]+(?=[A-Z][a-z]|[0-9]|$)|[A-Z]?[a-z]+|[0-9]+", str(value))
    return [part.casefold() for part in parts if part]


def _normalize_maxroll_identifier(value: object) -> str:
    """Normalize a Maxroll identifier for loose comparisons."""
    return "_".join(_tokenize_identifier(value))


def _collect_nested_values(value: object) -> list[object]:
    """Collect scalar values from nested Maxroll payload structures."""
    if isinstance(value, dict):
        nested_values: list[object] = []
        for nested_value in value.values():
            nested_values.extend(_collect_nested_values(nested_value))
        return nested_values

    if isinstance(value, list | tuple | set):
        nested_values = []
        for nested_item in value:
            nested_values.extend(_collect_nested_values(nested_item))
        return nested_values

    return [value]


def _extract_legendary_aspect_payload(resolved_item: dict, mapping_item: dict | None) -> object:
    """Return the most promising legendary-aspect payload for a Maxroll item."""
    aspect_payload_keys = (
        "legendaryPower",
        "legendaryPowers",
        "legendaryAspect",
        "legendaryAspects",
        "aspect",
        "aspects",
        "power",
        "powers",
        "powerId",
        "powerIds",
        "affix",
        "affixes",
        "affixId",
        "affixIds",
    )
    candidate_payloads: list[object] = []
    for source in (resolved_item, mapping_item or {}):
        candidate_payloads.extend(
            aspect_payload
            for aspect_payload_key in aspect_payload_keys
            if (aspect_payload := source.get(aspect_payload_key))
        )

    if candidate_payloads:
        return candidate_payloads[0] if len(candidate_payloads) == 1 else candidate_payloads

    fallback_sources: list[dict] = []
    if resolved_item:
        fallback_sources.append(resolved_item)
    if mapping_item:
        fallback_sources.append(mapping_item)
    return fallback_sources or None


def _log_unsupported_affix_attribute(attribute_name: str, missing_source: str) -> None:
    """Log an unsupported Maxroll affix attribute once per unique attribute name."""
    logged_key = f"{missing_source}:{attribute_name}"
    if logged_key in _LOGGED_UNSUPPORTED_AFFIX_ATTRIBUTES:
        return

    LOGGER.warning(
        f"Skipping unsupported Maxroll affix attribute '{attribute_name}' because it is not present in "
        f"{missing_source}."
    )
    _LOGGED_UNSUPPORTED_AFFIX_ATTRIBUTES.add(logged_key)


def _find_item_affixes(mapping_data: dict, item_affixes: dict, import_greater_affixes: bool = False) -> list[Affix]:
    """Resolve Maxroll item affixes into d4lf affix objects."""
    resolved_affixes = []
    for affix_id in item_affixes:
        for affix in mapping_data["affixes"].values():
            if affix["id"] != affix_id["nid"]:
                continue
            if affix["magicType"] in [2, 4]:
                break

            attr_desc = _attr_desc_special_handling(affix["id"])
            if not attr_desc:
                primary_attribute = affix["attributes"][0]
                attribute_formula = primary_attribute.get("formula")
                if attribute_formula in {
                    "Affix40%_SingleResist",
                    "AffixFlatResourceUpto4",
                    "AffixResourceOnKill",
                    "AffixSingleResist",
                    "S04_AffixResistance_Single_Flat",
                }:
                    if attribute_formula in {
                        "Affix40%_SingleResist",
                        "AffixSingleResist",
                        "S04_AffixResistance_Single_Flat",
                    }:
                        attr_desc = (
                            mapping_data["uiStrings"]["damageType"][str(primary_attribute["param"])] + " Resistance"
                        )
                    elif attribute_formula == "AffixFlatResourceUpto4":
                        resource_param = str(primary_attribute["param"])
                        attr_desc = (
                            "Faith per Second"
                            if resource_param == "9"
                            else mapping_data["uiStrings"]["resourceType"][resource_param] + " per Second"
                        )
                    elif attribute_formula == "AffixResourceOnKill":
                        attr_desc = (
                            mapping_data["uiStrings"]["resourceType"][str(primary_attribute["param"])] + " On Kill"
                        )
                elif "param" not in primary_attribute:
                    attr_id = str(primary_attribute["id"])
                    attr_obj = mapping_data["attributes"].get(attr_id)
                    if attr_obj is None:
                        _log_unsupported_affix_attribute(attr_id, "attributes")
                        break

                    if attr_obj["name"] == "Affix_Value_1":
                        attr_desc = "Faith per Second"
                    else:
                        attribute_name = _corrections(str(attr_obj["name"]))
                        attr_desc = mapping_data["attributeDescriptions"].get(attribute_name)
                        if not attr_desc:
                            _log_unsupported_affix_attribute(attribute_name, "attributeDescriptions")
                            break
                else:
                    attr_param = primary_attribute["param"]
                    for skill_data in mapping_data["skills"].values():
                        if skill_data["id"] == attr_param:
                            attr_desc = f"to {skill_data['name']}"
                            break
                    else:
                        if primary_attribute["param"] == -1460542966 and primary_attribute["id"] == 1033:
                            attr_desc = "to core skills"
                        elif primary_attribute["param"] == -755407686 and primary_attribute["id"] in [1034, 1091]:
                            attr_desc = "to defensive skills"
                        elif primary_attribute["param"] == 746476422 and primary_attribute["id"] == 1034:
                            attr_desc = "to mastery skills"
                        elif primary_attribute["param"] == -954965341 and primary_attribute["id"] == 1091:
                            attr_desc = "to basic skills"
                        elif primary_attribute["param"] == -1460608310 and primary_attribute["id"] == 1138:
                            attr_desc = "to aura skills"

            if not attr_desc:
                break

            clean_desc = re.sub(r"\[.*?\]|[^a-zA-Z ]", "", attr_desc)
            clean_desc = clean_desc.replace("SecondSeconds", "seconds")
            affix_obj = Affix(name=closest_match(clean_str(clean_desc), Dataloader().affix_dict))
            if import_greater_affixes and affix_id.get("greater", False):
                affix_obj.type = AffixType.greater

            if affix_obj.name is not None:
                resolved_affixes.append(affix_obj)
            elif "formula" in affix["attributes"][0] and affix["attributes"][0]["formula"] in [
                "InherentAffixAnyResist_Ring"
            ]:
                LOGGER.info("Skipping InherentAffixAnyResist_Ring")
            else:
                LOGGER.error(f"Couldn't match {affix_id=}")
            break
    return resolved_affixes


def _find_legendary_aspect_from_explicit_affixes(mapping_data: dict, item_explicit_affixes: list[dict]) -> str | None:
    """Resolve a legendary aspect by inspecting explicit affix ids on an item."""
    for item_explicit_affix in item_explicit_affixes:
        explicit_affix_id = item_explicit_affix.get("nid")
        if explicit_affix_id is None:
            continue

        for affix in mapping_data["affixes"].values():
            if affix.get("id") != explicit_affix_id or affix.get("magicType") != 1:
                continue

            if resolved_affix_name := _resolve_legendary_aspect_name(affix):
                return resolved_affix_name
            return None

    return None


def _find_legendary_aspect(mapping_data: dict, legendary_aspect: dict | list | str | None) -> str | None:
    """Resolve a Maxroll legendary aspect payload into a d4lf aspect name."""
    if not legendary_aspect:
        return None

    raw_candidate_values = [candidate for candidate in _collect_nested_values(legendary_aspect) if candidate]
    numeric_candidates = {
        str(candidate) for candidate in raw_candidate_values if isinstance(candidate, int) or str(candidate).isdigit()
    }
    normalized_text_candidates = {
        _normalize_maxroll_identifier(candidate).strip("_")
        for candidate in raw_candidate_values
        if isinstance(candidate, str) and candidate.strip()
    }

    aspect_name_lookup = {
        _normalize_maxroll_identifier(aspect_name).strip("_"): aspect_name for aspect_name in Dataloader().aspect_list
    }

    for affix in mapping_data["affixes"].values():
        if str(affix["id"]) in numeric_candidates:
            return _resolve_legendary_aspect_name(affix)

    for affix in mapping_data["affixes"].values():
        affix_candidates = {
            _normalize_maxroll_identifier(affix.get("name", "")).strip("_"),
            _normalize_maxroll_identifier(affix.get("prefix", "")).strip("_"),
            _normalize_maxroll_identifier(affix.get("suffix", "")).strip("_"),
        }
        resolved_affix_name = _resolve_legendary_aspect_name(affix)
        if resolved_affix_name:
            affix_candidates.add(_normalize_maxroll_identifier(resolved_affix_name).strip("_"))
        if normalized_text_candidates & {candidate for candidate in affix_candidates if candidate}:
            return resolved_affix_name

    for normalized_candidate in normalized_text_candidates:
        if normalized_candidate in aspect_name_lookup:
            return aspect_name_lookup[normalized_candidate]

    for candidate in raw_candidate_values:
        if isinstance(candidate, str) and candidate.strip():
            normalized_candidate = _normalize_maxroll_identifier(candidate).strip("_")
            if normalized_candidate in aspect_name_lookup:
                return aspect_name_lookup[normalized_candidate]
            if "aspect" in normalized_candidate or normalized_candidate.startswith("of_"):
                return _normalize_legendary_aspect_name(candidate)

    return None


def _normalize_legendary_aspect_name(name: str) -> str:
    """Normalize a Maxroll legendary aspect name into the d4lf naming style."""
    return correct_name(name).strip("_")


def _resolve_legendary_aspect_name(affix: dict) -> str | None:
    """Return the canonical d4lf aspect name from a Maxroll affix payload."""
    if "prefix" in affix:
        return _normalize_legendary_aspect_name(str(affix["prefix"]))
    if "suffix" in affix:
        return _normalize_legendary_aspect_name(str(affix["suffix"]))
    if "name" in affix:
        return _normalize_legendary_aspect_name(str(affix["name"]))
    return None


def _attr_desc_special_handling(affix_id: str) -> str:
    """Handle Maxroll affix ids that need manual description overrides."""
    match affix_id:
        case 1014505 | 2051010:
            return "evade grants movement speed for second"
        case 2057810:
            return "damage reduction from bleeding enemies"
        case 2067844:
            return "maximum poison resistance"
        case 2037914:
            return "subterfuge cooldown reduction"
        case 2123788:
            return "chance for core skills to hit twice"
        case 2119054:
            return "chance for basic skills to deal double damage"
        case 2119058:
            return "basic lucky hit chance"
        case 2052125:
            return "non-physical damage"
        case _:
            return ""


def _unique_name_special_handling(unique_name: str) -> str:
    """Apply known Maxroll-to-d4lf unique name corrections."""
    match unique_name:
        case "[PH] Season 7 Necro Pants":
            return "kessimes_legacy"
        case "[PH] Season 7 Barb Chest":
            return "mantle_of_mountains_fury"
        case _:
            return unique_name.replace("\xa0", " ")


def _find_item_type(mapping_data: dict, value: str) -> ItemType | None:
    """Resolve a Maxroll item identifier into a d4lf ItemType."""
    if (direct_match := _resolve_item_type_from_mapping_item(value, mapping_data.get(value))) is not None:
        return direct_match

    normalized_value = _normalize_maxroll_identifier(value)
    for item_key, item_data in mapping_data.items():
        lookup_candidates = {
            _normalize_maxroll_identifier(item_key),
            _normalize_maxroll_identifier(item_data.get("id", "")),
            _normalize_maxroll_identifier(item_data.get("name", "")),
            _normalize_maxroll_identifier(item_data.get("type", "")),
            _normalize_maxroll_identifier(item_data.get("slot", "")),
        }
        if normalized_value not in {candidate for candidate in lookup_candidates if candidate}:
            continue

        if (item_type := _resolve_item_type_from_mapping_item(item_key, item_data)) is not None:
            return item_type

    if (fallback_item_type := _resolve_item_type_from_identifier(value)) is not None:
        return fallback_item_type

    LOGGER.error("Couldn't match item type to enum")
    return None


def _resolve_item_type_from_mapping_item(item_key: str, item_data: dict | None) -> ItemType | None:
    """Resolve an ItemType from a Maxroll mapping-data item entry."""
    if item_data is None:
        return None

    raw_candidates = [
        item_data.get("type", ""),
        item_data.get("slot", ""),
        item_data.get("name", ""),
        item_key,
        item_data.get("id", ""),
    ]
    for raw_candidate in raw_candidates:
        candidate = str(raw_candidate).strip()
        if not candidate:
            continue
        if (item_type := match_to_enum(enum_class=ItemType, target_string=candidate, check_keys=True)) is not None:
            return item_type
        if (
            item_type := match_to_enum(enum_class=ItemType, target_string=candidate.replace("_", " "), check_keys=True)
        ) is not None:
            return item_type
        if (item_type := _resolve_item_type_from_identifier(candidate)) is not None:
            return item_type

    return None


def _resolve_item_type_from_identifier(identifier: str) -> ItemType | None:
    """Infer an ItemType from a generic Maxroll identifier."""
    token_set = set(_tokenize_identifier(identifier))
    explicit_token_mapping = (
        ("focus", ItemType.Focus),
        ("shield", ItemType.Shield),
        ("totem", ItemType.OffHandTotem),
        ("tome", ItemType.Tome),
    )
    for token, item_type in explicit_token_mapping:
        if token in token_set:
            return item_type

    for item_type in ItemType:
        item_type_tokens = set(_tokenize_identifier(item_type.name))
        if item_type_tokens and item_type_tokens.issubset(token_set):
            return item_type

    return None


def _extract_planner_url_and_id_from_planner(url: str) -> tuple[str, int]:
    """Extract the Maxroll planner API url and selected profile index from a planner url."""
    planner_suffix = url.split(PLANNER_BASE_URL)
    if len(planner_suffix) != 2:
        LOGGER.error(msg := "Invalid planner url")
        raise MaxrollException(msg)
    if "#" in planner_suffix[1]:
        planner_id, data_id = planner_suffix[1].split("#")
        data_id = int(data_id) - 1
    else:
        planner_id = planner_suffix[1]

        try:
            response = get_with_retry(url=PLANNER_API_BASE_URL + planner_id)
        except ConnectionError as exc:
            LOGGER.exception(msg := "Couldn't get planner")
            raise MaxrollException(msg) from exc
        data_id = json.loads(response.json()["data"])["activeProfile"]
    return PLANNER_API_BASE_URL + planner_id, data_id


def _extract_planner_url_and_id_from_guide(url: str) -> tuple[str, int]:
    """Extract the planner API url and selected profile index from a Maxroll build guide."""
    try:
        response = get_with_retry(url=url)
    except ConnectionError as exc:
        LOGGER.exception(msg := "Couldn't get build guide")
        raise MaxrollException(msg) from exc
    data = lxml.html.fromstring(response.text)
    msg = "Couldn't find planner url in build guide. Use planner link directly and report bug"
    if not (embed := data.xpath(BUILD_GUIDE_PLANNER_EMBED_XPATH)):
        LOGGER.error(msg)
        raise MaxrollException(msg)

    planner_id = embed[0].get("data-d4-profile")
    if not planner_id:
        LOGGER.error(msg)
        raise MaxrollException(msg)

    data_id_attr = embed[0].get("data-d4-id")
    if data_id_attr:
        return PLANNER_API_BASE_URL + planner_id, int(data_id_attr.split(",")[0]) - 1

    data_attr = embed[0].get("data-d4-data")
    if data_attr:
        return PLANNER_API_BASE_URL + planner_id, int(data_attr.split(",")[0]) - 1

    try:
        response = get_with_retry(url=PLANNER_API_BASE_URL + planner_id)
    except ConnectionError as exc:
        LOGGER.exception(msg)
        raise MaxrollException(msg) from exc

    try:
        data_id = json.loads(response.json()["data"])["activeProfile"]
    except Exception as ex:
        LOGGER.exception(msg)
        raise MaxrollException(msg) from ex

    return PLANNER_API_BASE_URL + planner_id, data_id


if __name__ == "__main__":
    src.logger.setup()
    URLS = ["https://maxroll.gg/d4/planner/19390ugy#1"]
    for url in URLS:
        config = ImportConfig(
            url=url,
            import_uniques=True,
            import_aspect_upgrades=True,
            add_to_profiles=False,
            import_greater_affixes=True,
            require_greater_affixes=True,
            export_paragon=False,
            custom_file_name=None,
        )
        import_maxroll(config)
