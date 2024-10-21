import json
import logging
import re

import lxml.html

import src.logger
from src.config.models import AffixFilterCountModel, AffixFilterModel, AspectUniqueFilterModel, ItemFilterModel, ProfileModel, UniqueModel
from src.dataloader import Dataloader
from src.gui.importer.common import get_with_retry, match_to_enum, retry_importer, save_as_profile
from src.item.data.affix import Affix
from src.item.data.item_type import ItemType
from src.item.descr.text import clean_str, closest_match

LOGGER = logging.getLogger(__name__)

BUILD_GUIDE_BASE_URL = "https://maxroll.gg/d4/build-guides/"
BUILD_GUIDE_PLANNER_EMBED_XPATH = "//*[contains(@class, 'd4-embed')]"
PLANNER_API_BASE_URL = "https://planners.maxroll.gg/profiles/d4/"
PLANNER_API_DATA_URL = "https://assets-ng.maxroll.gg/d4-tools/game/data.min.json"
PLANNER_BASE_URL = "https://maxroll.gg/d4/planner/"


class MaxrollException(Exception):
    pass


@retry_importer
def import_maxroll(url: str):
    url = url.strip().replace("\n", "")
    if PLANNER_BASE_URL not in url and BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a maxroll build guide or maxroll planner url")
        return
    LOGGER.info(f"Loading {url}")
    api_url, build_id = (
        _extract_planner_url_and_id_from_guide(url) if BUILD_GUIDE_BASE_URL in url else _extract_planner_url_and_id_from_planner(url)
    )
    try:
        r = get_with_retry(url=api_url)
    except ConnectionError:
        LOGGER.error("Couldn't get planner")
        return
    all_data = r.json()
    build_name = all_data["name"]
    build_data = json.loads(all_data["data"])
    items = build_data["items"]
    try:
        mapping_data = get_with_retry(url=PLANNER_API_DATA_URL).json()
    except ConnectionError:
        LOGGER.error("Couldn't get planner data")
        return
    active_profile = build_data["profiles"][build_id]
    finished_filters = []
    unique_filters = []
    for item_id in active_profile["items"].values():
        item_filter = ItemFilterModel()
        resolved_item = items[str(item_id)]
        if (item_type := _find_item_type(mapping_data=mapping_data["items"], value=resolved_item["id"])) is None:
            LOGGER.error("Couldn't find item type")
            return
        item_filter.itemType = [item_type]
        # magic/rare = 0, legendary = 1, unique = 2, mythic = 4
        if resolved_item["id"] in mapping_data["items"] and mapping_data["items"][resolved_item["id"]]["magicType"] in [2, 4]:
            unique_model = UniqueModel()
            unique_name = mapping_data["items"][resolved_item["id"]]["name"]
            try:
                unique_model.aspect = AspectUniqueFilterModel(name=unique_name)
                unique_model.affix = [
                    AffixFilterModel(name=x.name)
                    for x in _find_item_affixes(mapping_data=mapping_data, item_affixes=resolved_item["explicits"])
                ]
                unique_filters.append(unique_model)
            except Exception:
                LOGGER.exception(f"Unexpected error importing unique {unique_name}, please report a bug.")
            continue
        item_filter.affixPool = [
            AffixFilterCountModel(
                count=[
                    AffixFilterModel(name=x.name)
                    for x in _find_item_affixes(mapping_data=mapping_data, item_affixes=resolved_item["explicits"])
                ],
                minCount=2,
                minGreaterAffixCount=0,
            )
        ]
        item_filter.minPower = 100
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
    profile = ProfileModel(name="imported profile", Affixes=sorted(finished_filters, key=lambda x: next(iter(x))), Uniques=unique_filters)
    if not build_name:
        build_name = all_data["class"]
        if active_profile["name"]:
            build_name += f"_{active_profile["name"]}"
    save_as_profile(file_name=build_name, profile=profile, url=url)
    LOGGER.info("Finished")


def _corrections(input_str: str) -> str:
    match input_str:
        case "On_Hit_Vulnerable_Proc_Chance":
            return "On_Hit_Vulnerable_Proc"
        case "Movement_Bonus_On_Elite_Kill":
            return "Movement_Speed_Bonus_On_Elite_Kill"
    return input_str


def _find_item_affixes(mapping_data: dict, item_affixes: dict) -> list[Affix]:
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
                ]:
                    if affix["attributes"][0]["formula"] in ["Affix40%_SingleResist", "AffixSingleResist"]:
                        attr_desc = mapping_data["uiStrings"]["damageType"][str(affix["attributes"][0]["param"])] + " Resistance"
                    elif affix["attributes"][0]["formula"] in ["AffixFlatResourceUpto4"]:
                        attr_desc = mapping_data["uiStrings"]["resourceType"][str(affix["attributes"][0]["param"])] + " per Second"
                    elif affix["attributes"][0]["formula"] in ["AffixResourceOnKill"]:
                        attr_desc = mapping_data["uiStrings"]["resourceType"][str(affix["attributes"][0]["param"])] + " On Kill"
                elif "param" not in affix["attributes"][0]:
                    attr_id = affix["attributes"][0]["id"]
                    attr_obj = mapping_data["attributes"][str(attr_id)]
                    attr_desc = mapping_data["attributeDescriptions"][_corrections(attr_obj["name"])]
                else:  # must be + to talent or skill
                    attr_param = affix["attributes"][0]["param"]
                    for skill_data in mapping_data["skills"].values():
                        if skill_data["id"] == attr_param:
                            attr_desc = f"to {skill_data["name"]}"
                            break
                    else:
                        if affix["attributes"][0]["param"] == -1460542966 and affix["attributes"][0]["id"] == 1033:
                            attr_desc = "to core skills"
                        elif affix["attributes"][0]["param"] == -755407686 and affix["attributes"][0]["id"] in [1034, 1091]:
                            attr_desc = "to defensive skills"
                        elif affix["attributes"][0]["param"] == 746476422 and affix["attributes"][0]["id"] == 1034:
                            attr_desc = "to mastery skills"
                        elif affix["attributes"][0]["param"] == -954965341 and affix["attributes"][0]["id"] == 1091:
                            attr_desc = "to basic skills"
            clean_desc = re.sub(r"\[.*?\]|[^a-zA-Z ]", "", attr_desc)
            clean_desc = clean_desc.replace("SecondSeconds", "seconds")
            affix_obj = Affix(name=closest_match(clean_str(clean_desc), Dataloader().affix_dict))
            if affix_obj.name is not None:
                res.append(affix_obj)
            elif "formula" in affix["attributes"][0] and affix["attributes"][0]["formula"] in ["InherentAffixAnyResist_Ring"]:
                LOGGER.info("Skipping InherentAffixAnyResist_Ring")
            else:
                LOGGER.error(f"Couldn't match {affix_id=}")
            break
    return res


def _attr_desc_special_handling(affix_id: str) -> str:
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


def _find_item_type(mapping_data: dict, value: str) -> ItemType | None:
    for d_key, d_value in mapping_data.items():
        if d_key == value:
            if (res := match_to_enum(enum_class=ItemType, target_string=d_value["type"], check_keys=True)) is None:
                LOGGER.error("Couldn't match item type to enum")
                return None
            return res
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
    try:
        planner_id = embed[0].get("data-d4-profile")
        data_id = int(embed[0].get("data-d4-data").split(",")[0]) - 1
    except Exception as ex:
        LOGGER.exception(msg)
        raise MaxrollException(msg) from ex
    return PLANNER_API_BASE_URL + planner_id, data_id


if __name__ == "__main__":
    src.logger.setup()
    URLS = [
        "https://maxroll.gg/d4/build-guides/quill-volley-spiritborn-guide",
    ]
    for X in URLS:
        import_maxroll(url=X)
