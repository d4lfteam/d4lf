import logging
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import lxml.html

import src.logger
from src.config.models import AffixFilterCountModel, AffixFilterModel, AspectUniqueFilterModel, ItemFilterModel, ProfileModel, UniqueModel
from src.dataloader import Dataloader
from src.gui.importer.common import (
    add_to_profiles,
    fix_offhand_type,
    fix_weapon_type,
    get_class_name,
    get_with_retry,
    match_to_enum,
    retry_importer,
    save_as_profile,
)
from src.gui.importer.importer_config import ImportConfig
from src.item.data.affix import Affix
from src.item.data.item_type import WEAPON_TYPES, ItemType
from src.item.descr.text import clean_str, closest_match
from src.scripts.common import correct_name

LOGGER = logging.getLogger(__name__)

BUILD_GUIDE_ACTIVE_LOADOUT_XPATH = "//*[@class='m-fsuco1']"
BUILD_GUIDE_BASE_URL = "https://mobalytics.gg/diablo-4/"
BUILD_GUIDE_NAME_XPATH = "//*[@class='m-a53mf3']"
IMAGE_XPATH = ".//img"
ITEM_AFFIXES_EMPTY_XPATH = ".//*[@class='m-19epikr']"
ITEM_EMPTY_XPATH = ".//*[@class='m-16arb5z']"
ITEM_NAME_XPATH = ".//*[@class='m-ndz0o2']"
STATS_GRID_OCCUPIED_XPATH = ".//*[@class='m-0']"
STATS_GRID_XPATH = "//*[@class='m-4tf4x5']"
STATS_LIST_XPATH = ".//*[@class='m-qodgh2']"
TEMPERING_ICON_XPATH = ".//*[contains(@src, 'Tempreing.svg')]"


class MobalyticsException(Exception):
    pass


@retry_importer
def import_mobalytics(config: ImportConfig):
    url = config.url.strip().replace("\n", "")
    if BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a mobalytics build guide")
        return
    url = _fix_input_url(url=url)
    LOGGER.info(f"Loading {url}")
    try:
        r = get_with_retry(url=url, custom_headers={})
    except ConnectionError as exc:
        LOGGER.exception(msg := "Couldn't get build")
        raise MobalyticsException(msg) from exc
    data = lxml.html.fromstring(r.text)
    build_elem = data.xpath(BUILD_GUIDE_NAME_XPATH)
    if not build_elem:
        LOGGER.error(msg := "No build found")
        raise MobalyticsException(msg)
    build_name = build_elem[0].tail
    class_name = get_class_name(input_str=build_elem[0].text)
    if not (stats_grid := data.xpath(STATS_GRID_XPATH)):
        LOGGER.error(msg := "No stats grid found")
        raise MobalyticsException(msg)
    if not (items := stats_grid[0].xpath(STATS_GRID_OCCUPIED_XPATH)):
        LOGGER.error(msg := "No items found")
        raise MobalyticsException(msg)
    finished_filters = []
    unique_filters = []
    aspect_upgrade_filters = []
    for item in items:
        item_filter = ItemFilterModel()
        if not (name := item.xpath(ITEM_NAME_XPATH)):
            if item.xpath(ITEM_EMPTY_XPATH):
                continue
            LOGGER.error(msg := "No item name found")
            raise MobalyticsException(msg)
        if not (slot_elem := item.xpath(IMAGE_XPATH)):
            LOGGER.error(msg := "No item_type found")
            raise MobalyticsException(msg)
        slot = slot_elem[0].attrib["alt"]
        unique_name = name[0].text if "aspect" not in name[0].text.lower() else ""
        legendary_aspect = _get_legendary_aspect(name[0].text)
        if legendary_aspect:
            aspect_upgrade_filters.append(legendary_aspect)
        if not (stats := item.xpath(STATS_LIST_XPATH)):
            if item.xpath(ITEM_AFFIXES_EMPTY_XPATH):
                if unique_name:
                    LOGGER.warning(f"Unique {unique_name} had no affixes listed for it, only the aspect will be imported.")
                else:
                    continue
            else:
                LOGGER.error(msg := "No stats found")
                raise MobalyticsException(msg)
        item_type = None
        affixes = []
        inherents = []
        is_weapon = "weapon" in slot.lower()
        for stat in stats:
            if stat.xpath(TEMPERING_ICON_XPATH):
                continue
            affix_name = stat.xpath("./span")[0].text
            if is_weapon and (x := fix_weapon_type(input_str=affix_name)) is not None:
                item_type = x
                continue
            if "offhand" in slot.lower() and (x := fix_offhand_type(input_str=affix_name, class_str=class_name)) is not None:
                item_type = x
                if any(
                    substring in affix_name.lower() for substring in ["focus", "offhand", "shield", "totem"]
                ):  # special line indicating the item type
                    continue
            affix_obj = Affix(name=closest_match(clean_str(_corrections(input_str=affix_name)), Dataloader().affix_dict))
            if affix_obj.name is None:
                LOGGER.error(f"Couldn't match {affix_name=}")
                continue
            if (x := stat.xpath("./span/span")) and "implicit" in x[0].text.lower():
                inherents.append(affix_obj)
            else:
                affixes.append(affix_obj)

        if unique_name:
            unique_model = UniqueModel()
            try:
                unique_model.aspect = AspectUniqueFilterModel(name=unique_name)
                if affixes:
                    unique_model.affix = [AffixFilterModel(name=x.name) for x in affixes]
                unique_filters.append(unique_model)
            except Exception:
                LOGGER.exception(f"Unexpected error importing unique {unique_name}, please report a bug.")
            continue

        item_type = match_to_enum(enum_class=ItemType, target_string=re.sub(r"\d+", "", slot.lower())) if item_type is None else item_type
        if item_type is None:
            if is_weapon:
                LOGGER.warning(f"Couldn't find an item_type for weapon slot {slot}, defaulting to all weapon types instead.")
                item_filter.itemType = WEAPON_TYPES
            else:
                item_filter.itemType = []
                LOGGER.warning(f"Couldn't match item_type: {slot}. Please edit manually")
        else:
            item_filter.itemType = [item_type]

        item_filter.affixPool = [
            AffixFilterCountModel(
                count=[AffixFilterModel(name=x.name) for x in affixes],
                minCount=2,
                minGreaterAffixCount=0,
            )
        ]
        item_filter.minPower = 100
        if inherents:
            item_filter.inherentPool = [AffixFilterCountModel(count=[AffixFilterModel(name=x.name) for x in inherents])]
        filter_name_template = item_filter.itemType[0].name if item_type else slot.replace(" ", "")
        filter_name = filter_name_template
        i = 2
        while any(filter_name == next(iter(x)) for x in finished_filters):
            filter_name = f"{filter_name_template}{i}"
            i += 1
        finished_filters.append({filter_name: item_filter})
    profile = ProfileModel(name="imported profile", Affixes=sorted(finished_filters, key=lambda x: next(iter(x))))
    if config.import_uniques and unique_filters:
        profile.Uniques = unique_filters
    if config.import_aspect_upgrades and aspect_upgrade_filters:
        profile.AspectUpgrades = aspect_upgrade_filters

    if config.custom_file_name:
        build_name = config.custom_file_name

    build_name = build_name if build_name else f"{class_name}_{data.xpath(BUILD_GUIDE_ACTIVE_LOADOUT_XPATH)[0].text()}"
    corrected_file_name = save_as_profile(file_name=build_name, profile=profile, url=url)

    if config.add_to_profiles:
        add_to_profiles(corrected_file_name)

    LOGGER.info("Finished")


def _corrections(input_str: str) -> str:
    match input_str.lower():
        case "max life":
            return "maximum life"
    return input_str


def _fix_input_url(url: str) -> str:
    parsed_url = urlparse(url)
    query_dict = parse_qs(parsed_url.query)
    new_query_dict = {"equipmentTab": ["gear-stats"]}
    if "variantTab" in query_dict:
        new_query_dict["variantTab"] = query_dict["variantTab"]
    new_query_string = urlencode(new_query_dict, doseq=True)
    return urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, new_query_string, parsed_url.fragment))


def _get_legendary_aspect(name: str) -> str:
    if "aspect" in name.lower():
        aspect_name = correct_name(name.lower().replace("aspect", "").strip())

        if aspect_name not in Dataloader().aspect_list:
            LOGGER.warning(f"Legendary aspect '{aspect_name}' that is not in our aspect data, unable to add to AspectUpgrades.")
        else:
            return aspect_name
    return ""


if __name__ == "__main__":
    src.logger.setup()
    URLS = [
        "https://mobalytics.gg/diablo-4/builds/barbarian/bash",
        "https://mobalytics.gg/diablo-4/profile/3aeadb5c-522e-47b9-9a17-cdeaaa58909c/builds/4bb9a04e-da1e-449f-91ab-ca29e5727a20",
    ]
    for X in URLS:
        import_mobalytics(url=X)
