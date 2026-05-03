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
    add_to_profiles,
    build_default_profile_file_name,
    fix_offhand_type,
    fix_weapon_type,
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
PLANNER_API_BASE_URL = "https://planners.maxroll.gg/profiles/d4/"
PLANNER_API_DATA_URL = "https://assets-ng.maxroll.gg/d4-tools/game/data.min.json?aac01320"
PLANNER_BASE_URL = "https://maxroll.gg/d4/planner/"
SCRIPT_XPATH = "//div[@id='root']/script"
BUILD_SCRIPT_PREFIX = "window.__remixContext = "
PLANNER_API_REGEX = re.compile(r'(https://maxroll\.gg/d4/planner/[^"|\\]*)')


class MaxrollException(Exception):
    pass


@retry_importer
def import_maxroll(config: ImportConfig):
    url = config.url.strip().replace("\n", "")
    if PLANNER_BASE_URL not in url and BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a maxroll build guide or maxroll planner url")
        return
    LOGGER.info(f"Loading {url}")
    if BUILD_GUIDE_BASE_URL in url:
        api_url, build_id = _extract_planner_url_and_id_from_guide(url)
    else:
        api_url, build_id = _extract_planner_url_and_id_from_planner(url)
    try:
        r = get_with_retry(url=api_url)
    except ConnectionError:
        LOGGER.error("Couldn't get planner")
        return
    all_data = r.json()
    guide_season = all_data.get("season", "")
    build_data = json.loads(all_data["data"])
    items = build_data["items"]
    try:
        mapping_data = get_with_retry(url=PLANNER_API_DATA_URL).json()
    except ConnectionError:
        LOGGER.error("Couldn't get planner data")
        return
    # The attribute descriptions are not always consistent with the casing for the key so we fix that here
    mapping_data["attributeDescriptions"] = {k.lower(): v for k, v in mapping_data["attributeDescriptions"].items()}
    active_profile = build_data["profiles"][build_id]
    build_header = all_data["name"] or all_data["class"]
    variant_name = active_profile["name"] or ""
    build_name = build_header
    if not build_name:
        build_name = all_data["class"]
    if variant_name:
        build_name += f"_{variant_name}"
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
                # This will actually work now but I don't think it's what people will want, so leaving out for now
                # unique_model.affix = [
                #     AffixFilterModel(name=x.name)
                #     for x in _find_item_affixes(mapping_data=mapping_data, item_affixes=resolved_item["explicits"])
                # ]
                unique_filters.append(unique_model)
            except Exception:
                LOGGER.exception(f"Unexpected error importing unique {unique_name}, please report a bug.")
            continue

        item_filter = ItemFilterModel()
        if (
            item_type := _find_item_type(
                mapping_data=mapping_data["items"], value=resolved_item["id"], class_name=all_data["class"]
            )
        ) is None:
            LOGGER.warning(
                f"Couldn't find item type for {resolved_item['id']} from mapping data provided by Maxroll. Skipping item."
            )
            continue

        if item_type in [ItemType.HoradricSeal, ItemType.Charm]:
            LOGGER.warning(f"Seals and Charms are not currently supported, skipping {resolved_item['name']}.")
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

        # Standard item handling
        item_filter.affixPool = [
            AffixFilterCountModel(
                count=[
                    AffixFilterModel(name=x.name, want_greater=x.type == AffixType.greater)
                    for x in _find_item_affixes(
                        mapping_data=mapping_data,
                        item_affixes=resolved_item["explicits"],
                        item_type=item_type,
                        import_greater_affixes=config.import_greater_affixes,
                    )
                ],
                minCount=3,
            )
        ]
        item_filter.minPower = 100
        update_mingreateraffixcount(item_filter, config.require_greater_affixes)

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

    file_name = config.custom_file_name
    if not file_name:
        file_name = build_default_profile_file_name(
            source_name="maxroll",
            class_name=all_data["class"],
            season_number=guide_season,
            build_header=build_header,
            variant_name=variant_name,
        )

    # Optionally embed Paragon data into the profile model before saving
    if config.export_paragon:
        steps = extract_maxroll_paragon_steps(active_profile)
        if steps:
            profile.Paragon = build_paragon_profile_payload(
                build_name=build_name, source_url=url, paragon_boards_list=steps
            )
        else:
            LOGGER.warning("Paragon export enabled, but no paragon steps were found in this Maxroll profile.")

    corrected_file_name = save_as_profile(file_name=file_name, profile=profile, url=url)

    if config.add_to_profiles:
        add_to_profiles(corrected_file_name)

    LOGGER.info("Finished")


def _attribute_description_corrections(input_str: str) -> str:
    match input_str:
        case "On_Hit_Vulnerable_Proc_Chance":
            return "On_Hit_Vulnerable_Proc".lower()
        case "Movement_Bonus_On_Elite_Kill":
            return "Movement_Speed_Bonus_On_Elite_Kill".lower()
    return input_str.lower()


def _find_item_affixes(
    mapping_data: dict, item_affixes: dict, item_type: ItemType, import_greater_affixes=False
) -> list[Affix]:
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
                    "GearAffix_Resource_Per_Second",
                    "GearAffix_DamageType",
                    "GearAffix_DamageType_Greater",
                    "GearAffix_Resource_On_Kill",
                    "GearAffix_Resource_On_Kill_Warlock",
                ]:
                    if affix["attributes"][0]["formula"] in ["GearAffix_DamageType", "GearAffix_DamageType_Greater"]:
                        attr_desc = (
                            mapping_data["uiStrings"]["damageType"][str(affix["attributes"][0]["param"])]
                            + " Damage Multiplier"
                        )
                    elif affix["attributes"][0]["formula"] in ["GearAffix_Resource_Per_Second"]:
                        param = str(affix["attributes"][0]["param"])
                        attr_desc = mapping_data["uiStrings"]["resourceType"][param] + " Regeneration"
                    elif affix["attributes"][0]["formula"] in [
                        "GearAffix_Resource_On_Kill",
                        "GearAffix_Resource_On_Kill_Warlock",
                    ]:
                        attr_desc = (
                            mapping_data["uiStrings"]["resourceType"][str(affix["attributes"][0]["param"])] + " On Kill"
                        )
                elif "param" not in affix["attributes"][0]:
                    attr_id = affix["attributes"][0]["id"]
                    attr_obj = mapping_data["attributes"][str(attr_id)]
                    attr_desc = mapping_data["attributeDescriptions"].get(
                        _attribute_description_corrections(attr_obj["name"])
                    )
                    if not attr_desc:
                        LOGGER.warning(
                            f"Unable to map {attr_obj['name']} from MaxRoll data to an affix, skipping affix and please report a bug."
                        )
                        continue
                else:  # must be + to talent or skill
                    attr_param = affix["attributes"][0]["param"]
                    for skill_data in mapping_data["skills"].values():
                        if skill_data["id"] == attr_param:
                            attr_desc = f"to {skill_data['name']}"
                            break
                    else:
                        param_id = affix["attributes"][0]["param"]
                        attribute_id = affix["attributes"][0]["id"]
                        if param_id == -1460542966 and attribute_id in [1033, 1155]:
                            attr_desc = "to core skills"
                        elif param_id == -755407686 and attribute_id in [1034, 1091]:
                            attr_desc = "to defensive skills"
                        elif param_id == 746476422 and attribute_id == 1034:
                            attr_desc = "to mastery skills"
                        elif param_id == -954965341 and attribute_id == 1091:
                            attr_desc = "to basic skills"
                        elif param_id == -1460608310 and attribute_id == 1138:
                            attr_desc = "to aura skills"
                        elif param_id == 850110203 and attribute_id == 1155:
                            attr_desc = "to demonology skills"
            clean_desc = re.sub(r"\[.*?\]|[^a-zA-Z ]", "", attr_desc)
            clean_desc = clean_desc.replace("SecondSeconds", "seconds")
            if not clean_desc:
                LOGGER.warning(
                    f"We were unable to map an attribute on item type {item_type.value} to an affix. Please report a bug and include a link to the build, we are skipping that affix."
                )
                continue

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


def _find_item_type(mapping_data: dict, value: str, class_name: str = "") -> ItemType | None:
    for d_key, d_value in mapping_data.items():
        if d_key == value:
            item_type_str = d_value["type"]
            normalized_item_type_str = _normalize_item_type_str_for_import_helpers(item_type_str)
            if (item_type := fix_weapon_type(input_str=normalized_item_type_str)) is not None:
                return item_type
            if (
                any(substring in normalized_item_type_str for substring in ["focus", "off hand", "shield", "totem"])
            ) and (item_type := fix_offhand_type(input_str=normalized_item_type_str, class_str=class_name)) is not None:
                return item_type
            if (res := match_to_enum(enum_class=ItemType, target_string=item_type_str, check_keys=True)) is None:
                LOGGER.error("Couldn't match item type to enum")
                return None
            return res
    return None


def _normalize_item_type_str_for_import_helpers(item_type_str: str) -> str:
    normalized_item_type = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", item_type_str)
    normalized_item_type = re.sub(r"(?<=[A-Za-z])(?=[12]H\b)", " ", normalized_item_type)
    normalized_item_type = normalized_item_type.replace("-", " ").lower()
    normalized_item_type = " ".join(normalized_item_type.split())
    return re.sub(r"\b([a-z]+)\s+(1h|2h)\b", r"\2 \1", normalized_item_type)


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
    """Resolve a build guide to the underlying planner API url, active profile id, and guide season."""
    try:
        r = get_with_retry(url=url)
    except ConnectionError as exc:
        LOGGER.exception(msg := "Couldn't get build guide")
        raise MaxrollException(msg) from exc
    data = lxml.html.fromstring(r.text)
    # As of season 13, the link to the planner is stuck in a script so we get it from there
    script_elements = data.xpath(SCRIPT_XPATH)
    for script_element in script_elements:
        if script_element.text and script_element.text.strip().startswith(BUILD_SCRIPT_PREFIX):
            planner_link = PLANNER_API_REGEX.search(script_element.text).group()
            if planner_link:
                api_url, build_id = _extract_planner_url_and_id_from_planner(planner_link)
                return api_url, build_id

    msg = "Couldn't resolve a planner profile from this Maxroll build guide. Use the planner link directly and please report a bug."
    LOGGER.error(msg)
    raise MaxrollException(msg)


def _extract_guide_profile_id(embed: lxml.html.HtmlElement) -> int | None:
    if data_id := embed.get("data-d4-id"):
        return int(data_id.split(",")[0]) - 1
    if data_ids := embed.get("data-d4-data"):
        guide_profile_ids = [int(value) for value in data_ids.split(",") if value]
        if (active_tab_index := _extract_active_guide_embed_tab_index(embed)) is not None and active_tab_index < len(
            guide_profile_ids
        ):
            return guide_profile_ids[active_tab_index] - 1
        return guide_profile_ids[0] - 1
    return None


def _extract_active_guide_embed_tab_index(embed: lxml.html.HtmlElement) -> int | None:
    for index, tab in enumerate(embed.xpath(".//*[contains(@class, 'd4t-tabs')]/li")):
        if "d4t-active" in (tab.get("class") or ""):
            return index
    return None


if __name__ == "__main__":
    src.logger.setup()
    URLS = ["https://maxroll.gg/d4/build-guides/ball-lightning-sorcerer-guide"]
    for X in URLS:
        config = ImportConfig(
            url=X,
            import_uniques=True,
            import_aspect_upgrades=True,
            add_to_profiles=False,
            import_greater_affixes=True,
            require_greater_affixes=True,
            export_paragon=True,
            custom_file_name=None,
        )
        import_maxroll(config)
