import json
import logging
import re

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
from src.gui.importer.gui_common import (
    build_default_profile_name,
    get_class_name,
    get_with_retry,
    log_import_summary,
    match_to_enum,
    retry_importer,
    save_imported_profile,
    update_mingreateraffixcount,
)
from src.gui.importer.importer_config import ImportConfig, ImportVariantOption
from src.gui.importer.paragon_export import attach_paragon_payload, extract_maxroll_paragon_steps
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
_MAXROLL_ITEM_TYPE_PREFIX_ALIASES = {
    "1hfocus": ItemType.Focus,
    "1hshield": ItemType.Shield,
    "1htotem": ItemType.OffHandTotem,
    "focusbookoffhand": ItemType.Tome,
}


class MaxrollException(Exception):
    pass


@retry_importer
def import_maxroll(config: ImportConfig):
    try:
        url, all_data, build_data, build_id = _load_maxroll_build_data(config.url)
    except MaxrollException:
        return
    items = build_data["items"]
    try:
        mapping_data = get_with_retry(url=PLANNER_API_DATA_URL).json()
    except ConnectionError:
        LOGGER.error("Couldn't get planner data")
        return

    profile_indices = _resolve_profile_indices(
        url=url, build_data=build_data, selected_profile_index=build_id, config=config
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

        if config.export_paragon:
            attach_paragon_payload(
                profile,
                build_name=build_name,
                source_url=url,
                paragon_boards_list=extract_maxroll_paragon_steps(active_profile),
                missing_data_message="Paragon export enabled, but no paragon steps were found in this Maxroll profile.",
            )

        corrected_file_name = save_imported_profile(
            file_name=build_name, profile=profile, url=url, add_to_active_profiles=config.add_to_profiles
        )
        created_profiles.append(corrected_file_name)

    log_import_summary(LOGGER, "Maxroll", created_profiles)


def get_maxroll_variant_options(url: str) -> list[ImportVariantOption]:
    _, _, build_data, selected_profile_index = _load_maxroll_build_data(url)
    profiles = build_data.get("profiles", [])
    if not profiles:
        return [ImportVariantOption(id=str(selected_profile_index), label=f"profile_{selected_profile_index + 1}")]

    options = []
    for profile_index, profile in enumerate(profiles):
        if not profile.get("items"):
            continue
        label = str(profile.get("name", "")).strip() or f"profile_{profile_index + 1}"
        options.append(ImportVariantOption(id=str(profile_index), label=label))
    return options


def _load_maxroll_build_data(url: str) -> tuple[str, dict, dict, int]:
    url = url.strip().replace("\n", "")
    if PLANNER_BASE_URL not in url and BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a maxroll build guide or maxroll planner url")
        msg = "Invalid Maxroll URL"
        raise MaxrollException(msg)

    LOGGER.info(f"Loading {url}")
    api_url, build_id = (
        _extract_planner_url_and_id_from_guide(url)
        if BUILD_GUIDE_BASE_URL in url
        else _extract_planner_url_and_id_from_planner(url)
    )
    try:
        response = get_with_retry(url=api_url)
    except ConnectionError as exc:
        LOGGER.error("Couldn't get planner")
        msg = "Couldn't get planner"
        raise MaxrollException(msg) from exc

    all_data = response.json()
    build_data = json.loads(all_data["data"])
    return url, all_data, build_data, build_id


def _resolve_profile_indices(
    url: str, build_data: dict, selected_profile_index: int, config: ImportConfig
) -> list[int]:
    profiles = build_data.get("profiles", [])
    if not profiles:
        return [selected_profile_index]

    if not config.import_multiple_variants:
        return [selected_profile_index]

    importable_indices = [profile_index for profile_index, profile in enumerate(profiles) if profile.get("items")]
    if config.selected_variants:
        selected_indices = []
        for variant_id in config.selected_variants:
            try:
                profile_index = int(variant_id)
            except ValueError:
                continue
            if profile_index in importable_indices:
                selected_indices.append(profile_index)
        return selected_indices or [selected_profile_index]

    if len(importable_indices) > 1:
        LOGGER.info(f"Found {len(importable_indices)} Maxroll planner variants. Importing selected variants.")
    return importable_indices or [selected_profile_index]


def _resolve_output_file_name(
    config: ImportConfig, all_data: dict, active_profile: dict, build_id: int, import_count: int
) -> str:
    if not config.custom_file_name:
        return _build_default_file_name(all_data=all_data, active_profile=active_profile, build_id=build_id)

    if import_count <= 1:
        return config.custom_file_name

    variant_name = str(active_profile.get("name", "")).strip() or f"profile_{build_id + 1}"
    return f"{config.custom_file_name}_{variant_name}"


def _build_profile(active_profile: dict, items: dict, mapping_data: dict, config: ImportConfig) -> ProfileModel:
    finished_filters = []
    unique_filters = []
    aspect_upgrade_filters = []
    for item_id in active_profile["items"].values():
        resolved_item = items[str(item_id)]
        resolved_item_id = resolved_item["id"]
        # magic/rare = 0, legendary = 1, unique = 2, mythic = 4
        # Unique aspect handling
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
                # Maxroll's uniques are all over the place in quality when it comes to affixes and names.
                # Removing support for this for now.
                # unique_model.affix = [
                #     AffixFilterModel(name=x.name)
                #     for x in _find_item_affixes(mapping_data=mapping_data, item_affixes=resolved_item["explicits"])
                # ]
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

        # Legendary aspect upgrade handling
        if (
            resolved_item["id"] in mapping_data["items"]
            and mapping_data["items"][resolved_item["id"]]["magicType"] == 1
            and config.import_aspect_upgrades
        ):
            legendary_aspect = _find_legendary_aspect(
                mapping_data, resolved_item.get("legendaryPower", resolved_item.get("aspects", {}))
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
                # MaxRoll reports all rares as legendaries so this is an attempt to reduce false warnings for rares
                if len(resolved_item["explicits"]) == 3:
                    msg += (
                        " We suspect this item is actually a rare and maxroll is falsely reporting it as a legendary, "
                        "please double check."
                    )
                    LOGGER.debug(msg)
                else:
                    LOGGER.warning(msg)

        # Standard item handling
        item_filter.affixPool = [
            AffixFilterCountModel(
                count=[
                    AffixFilterModel(name=x.name, want_greater=x.type == AffixType.greater)
                    for x in _find_item_affixes(
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

        # maxroll has some outdated data, so we need to clean it up by using item_type
        if "implicits" in resolved_item and item_type in [ItemType.Boots]:
            item_filter.inherentPool = [
                AffixFilterCountModel(
                    count=[
                        AffixFilterModel(name=x.name)
                        for x in _find_item_affixes(mapping_data=mapping_data, item_affixes=resolved_item["implicits"])
                    ]
                )
            ]
        filter_name = item_filter.itemType[0].name
        i = 2
        while any(filter_name == next(iter(x)) for x in finished_filters):
            filter_name = f"{item_filter.itemType[0].name}{i}"
            i += 1

        finished_filters.append({filter_name: item_filter})

    profile = ProfileModel(name="imported profile", Affixes=sorted(finished_filters, key=lambda x: next(iter(x))))
    if config.import_uniques and unique_filters:
        profile.Uniques = unique_filters
    if config.import_aspect_upgrades and aspect_upgrade_filters:
        profile.AspectUpgrades = aspect_upgrade_filters
    return profile


def _build_default_file_name(all_data: dict, active_profile: dict, build_id: int) -> str:
    class_name = get_class_name(str(all_data.get("class", "")))
    build_name = str(all_data.get("name", "")).strip() or class_name
    variant_name = str(active_profile.get("name", "")).strip()
    variant_suffix = variant_name or (f"profile_{build_id + 1}" if active_profile.get("items") else "")
    fallback = class_name if class_name and class_name != "Unknown" else f"profile_{build_id + 1}"
    return build_default_profile_name("maxroll", build_name, variant_suffix, fallback=fallback)


def _corrections(input_str: str) -> str:
    match input_str:
        case "On_Hit_Vulnerable_Proc_Chance":
            return "On_Hit_Vulnerable_Proc"
        case "Movement_Bonus_On_Elite_Kill":
            return "Movement_Speed_Bonus_On_Elite_Kill"
    return input_str


def _find_item_affixes(mapping_data: dict, item_affixes: dict, import_greater_affixes=False) -> list[Affix]:
    res = []
    for affix_id in item_affixes:
        for affix in mapping_data["affixes"].values():
            if affix["id"] != affix_id["nid"]:
                continue
            if affix["magicType"] in [2, 4]:
                break
            attr_desc = _attr_desc_special_handling(affix["id"])
            if not attr_desc:
                if "formula" in affix["attributes"][0] and affix["attributes"][0]["formula"] in [
                    "Affix40%_SingleResist",
                    "AffixFlatResourceUpto4",
                    "AffixResourceOnKill",
                    "AffixSingleResist",
                    "S04_AffixResistance_Single_Flat",
                ]:
                    if affix["attributes"][0]["formula"] in [
                        "Affix40%_SingleResist",
                        "AffixSingleResist",
                        "S04_AffixResistance_Single_Flat",
                    ]:
                        attr_desc = (
                            mapping_data["uiStrings"]["damageType"][str(affix["attributes"][0]["param"])]
                            + " Resistance"
                        )
                    elif affix["attributes"][0]["formula"] in ["AffixFlatResourceUpto4"]:
                        param = str(affix["attributes"][0]["param"])
                        # Maxroll doesn't have Faith in their data
                        attr_desc = (
                            "Faith per Second"
                            if param == "9"
                            else mapping_data["uiStrings"]["resourceType"][param] + " per Second"
                        )
                    elif affix["attributes"][0]["formula"] in ["AffixResourceOnKill"]:
                        attr_desc = (
                            mapping_data["uiStrings"]["resourceType"][str(affix["attributes"][0]["param"])] + " On Kill"
                        )
                elif "param" not in affix["attributes"][0]:
                    attr_id = affix["attributes"][0]["id"]
                    attr_obj = mapping_data["attributes"][str(attr_id)]
                    # Maxroll continues to not know what faith per second is
                    attr_desc = (
                        "Faith per Second"
                        if attr_obj["name"] == "Affix_Value_1"
                        else mapping_data["attributeDescriptions"][_corrections(attr_obj["name"])]
                    )
                else:  # must be + to talent or skill
                    attr_param = affix["attributes"][0]["param"]
                    for skill_data in mapping_data["skills"].values():
                        if skill_data["id"] == attr_param:
                            attr_desc = f"to {skill_data['name']}"
                            break
                    else:
                        if affix["attributes"][0]["param"] == -1460542966 and affix["attributes"][0]["id"] == 1033:
                            attr_desc = "to core skills"
                        elif affix["attributes"][0]["param"] == -755407686 and affix["attributes"][0]["id"] in [
                            1034,
                            1091,
                        ]:
                            attr_desc = "to defensive skills"
                        elif affix["attributes"][0]["param"] == 746476422 and affix["attributes"][0]["id"] == 1034:
                            attr_desc = "to mastery skills"
                        elif affix["attributes"][0]["param"] == -954965341 and affix["attributes"][0]["id"] == 1091:
                            attr_desc = "to basic skills"
                        elif affix["attributes"][0]["param"] == -1460608310 and affix["attributes"][0]["id"] == 1138:
                            attr_desc = "to aura skills"
            clean_desc = re.sub(r"\[.*?\]|[^a-zA-Z ]", "", attr_desc)
            clean_desc = clean_desc.replace("SecondSeconds", "seconds")
            affix_obj = Affix(name=closest_match(clean_str(clean_desc), Dataloader().affix_dict))
            if import_greater_affixes and affix_id.get("greater", False):
                affix_obj.type = AffixType.greater
            if affix_obj.name is not None:
                res.append(affix_obj)
            elif "formula" in affix["attributes"][0] and affix["attributes"][0]["formula"] in [
                "InherentAffixAnyResist_Ring"
            ]:
                LOGGER.info("Skipping InherentAffixAnyResist_Ring")
            else:
                LOGGER.error(f"Couldn't match {affix_id=}")
            break
    return res


def _find_legendary_aspect(mapping_data: dict, legendary_aspect: dict) -> str | None:
    if not legendary_aspect:
        return None

    if isinstance(legendary_aspect, list):
        legendary_aspect = legendary_aspect[0]

    for affix in mapping_data["affixes"].values():
        if affix["id"] != legendary_aspect["nid"]:
            continue

        if "prefix" in affix:
            return correct_name(affix["prefix"])
        if "suffix" in affix:
            return correct_name(affix["suffix"])
        return None

    return None


def _attr_desc_special_handling(affix_id: str) -> str:
    match affix_id:
        case 1014505 | 2051010:
            return "evade grants movement speed for second"
        case 2568489:
            return "hunger increased reputation from kill streaks"
        case 2568491:
            return "hunger increased experience from kill streaks"
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
    match unique_name:
        case "[PH] Season 7 Necro Pants":
            return "kessimes_legacy"
        case "[PH] Season 7 Barb Chest":
            return "mantle_of_mountains_fury"
        case _:
            return unique_name.replace("\xa0", " ")


def _find_item_type(mapping_data: dict, value: str) -> ItemType | None:
    for d_key, d_value in mapping_data.items():
        if d_key == value:
            if (res := match_to_enum(enum_class=ItemType, target_string=d_value["type"], check_keys=True)) is not None:
                return res
            if (res := _match_maxroll_item_type_alias(d_value["type"])) is not None:
                return res
            if (res := _match_maxroll_item_type_alias(value)) is not None:
                return res
            LOGGER.error("Couldn't match item type to enum")
            return None
    return None


def _match_maxroll_item_type_alias(raw_value: str) -> ItemType | None:
    normalized_value = re.sub(r"[^a-z0-9]", "", str(raw_value or "").lower())
    for prefix, item_type in _MAXROLL_ITEM_TYPE_PREFIX_ALIASES.items():
        if normalized_value.startswith(prefix):
            return item_type
    return None


def _extract_planner_url_and_id_from_planner(url: str) -> tuple[str, int]:
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
            r = get_with_retry(url=PLANNER_API_BASE_URL + planner_id)
        except ConnectionError as exc:
            LOGGER.exception(msg := "Couldn't get planner")
            raise MaxrollException(msg) from exc
        data_id = json.loads(r.json()["data"])["activeProfile"]
    return PLANNER_API_BASE_URL + planner_id, data_id


def _extract_planner_url_and_id_from_guide(url: str) -> tuple[str, int]:
    try:
        r = get_with_retry(url=url)
    except ConnectionError as exc:
        LOGGER.exception(msg := "Couldn't get build guide")
        raise MaxrollException(msg) from exc
    data = lxml.html.fromstring(r.text)
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
        r = get_with_retry(url=PLANNER_API_BASE_URL + planner_id)
    except ConnectionError as exc:
        LOGGER.exception(msg)
        raise MaxrollException(msg) from exc

    try:
        data_id = json.loads(r.json()["data"])["activeProfile"]
    except Exception as ex:
        LOGGER.exception(msg)
        raise MaxrollException(msg) from ex

    return PLANNER_API_BASE_URL + planner_id, data_id


if __name__ == "__main__":
    src.logger.setup()
    URLS = ["https://maxroll.gg/d4/planner/19390ugy#1"]
    for X in URLS:
        config = ImportConfig(
            url=X,
            import_uniques=True,
            import_aspect_upgrades=True,
            add_to_profiles=False,
            import_greater_affixes=True,
            require_greater_affixes=True,
            export_paragon=False,
            custom_file_name=None,
        )
        import_maxroll(config)
