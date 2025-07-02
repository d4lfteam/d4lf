import datetime
import logging
import re
import time

import lxml.html
from selenium.webdriver.chromium.webdriver import ChromiumDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import src.logger
from src.config.models import AffixFilterCountModel, AffixFilterModel, AspectUniqueFilterModel, ItemFilterModel, ProfileModel, UniqueModel
from src.dataloader import Dataloader
from src.gui.importer.common import (
    add_to_profiles,
    fix_offhand_type,
    fix_weapon_type,
    get_class_name,
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

BASE_URL = "https://d4builds.gg/builds"
BUILD_OVERVIEW_XPATH = "//*[@class='builder__stats__list']"
CLASS_XPATH = "//*[contains(@class, 'builder__header__description')]"
ITEM_GROUP_XPATH = ".//*[contains(@class, 'builder__stats__group')]"
ITEM_SLOT_XPATH = ".//*[contains(@class, 'builder__stats__slot')]"
ITEM_STATS_XPATH = ".//*[contains(@class, 'dropdown__button__wrapper')]"
PAPERDOLL_ITEM_SLOT_XPATH = ".//*[contains(@class, 'builder__gear__slot')]"
PAPERDOLL_ITEM_UNIQUE_NAME_XPATH = ".//*[contains(@class, 'builder__gear__name--')]"
PAPERDOLL_ITEM_XPATH = ".//*[contains(@class, 'builder__gear__item') and not(contains(@class, 'disabled'))]"
PAPERDOLL_LEGENDARY_ASPECT_XPATH = "//*[@class='builder__gear__name' and not(contains(@class, 'builder__gear__name--'))]"
PAPERDOLL_XPATH = "//*[contains(@class, 'builder__gear__items')]"
TEMPERING_ICON_XPATH = ".//*[contains(@src, 'tempering_02.png')]"
UNIQUE_ICON_XPATH = ".//*[contains(@src, '/Uniques/')]"


class D4BuildsException(Exception):
    pass


@retry_importer(inject_webdriver=True)
def import_d4builds(config: ImportConfig, driver: ChromiumDriver = None):
    url = config.url.strip().replace("\n", "")
    if BASE_URL not in url:
        LOGGER.error("Invalid url, please use a d4builds url")
        return
    LOGGER.info(f"Loading {url}")
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.XPATH, BUILD_OVERVIEW_XPATH)))
    wait.until(EC.presence_of_element_located((By.XPATH, PAPERDOLL_XPATH)))
    time.sleep(5)  # super hacky but I didn't find anything else. The page is not fully loaded when the above wait is done
    data = lxml.html.fromstring(driver.page_source)
    if (elem := data.xpath(CLASS_XPATH + "/*")) or (elem := data.xpath(CLASS_XPATH)):  # noqa SIM114
        class_name = get_class_name(f"{elem[0].tail} {elem[0].text}")
    else:
        class_name = "Unknown"
    if not (items := data.xpath(BUILD_OVERVIEW_XPATH)):
        LOGGER.error(msg := "No items found")
        raise D4BuildsException(msg)
    slot_to_unique_name_map = _get_item_slots(data=data)
    finished_filters = []
    unique_filters = []
    aspect_upgrade_filters = _get_legendary_aspects(data=data)
    for item in items[0]:
        item_filter = ItemFilterModel()
        if not (slot := item.xpath(ITEM_SLOT_XPATH)[1].tail):
            LOGGER.error("No item_type found")
            continue
        if slot not in slot_to_unique_name_map:
            LOGGER.warning(f"Empty slots are not supported. Skipping: {slot}")
            continue
        if not (stats := item.xpath(ITEM_STATS_XPATH)):
            LOGGER.error(f"No stats found for {slot=}")
            continue
        item_type = None
        affixes = []
        inherents = []
        is_weapon = "weapon" in slot.lower()
        for stat in stats:
            if stat.xpath(TEMPERING_ICON_XPATH):
                continue
            if "filled" not in stat.xpath("../..")[0].attrib["class"]:
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
            if ("ring" in slot.lower() and any(substring in affix_name.lower() for substring in ["resistance"])) or (
                "boots" in slot.lower() and any(substring in affix_name.lower() for substring in ["max evade charges", "attacks reduce"])
            ):
                inherents.append(affix_obj)
            else:
                affixes.append(affix_obj)

        if slot_to_unique_name_map[slot]:
            unique_model = UniqueModel()
            unique_name = slot_to_unique_name_map[slot]
            try:
                unique_model.aspect = AspectUniqueFilterModel(name=unique_name)
                unique_model.affix = [AffixFilterModel(name=x.name) for x in affixes]
                unique_filters.append(unique_model)
            except Exception:
                LOGGER.exception(
                    f"Unexpected error importing unique {unique_name}, please report a bug and include a link to the build you were trying to import."
                )
            continue

        if not affixes:
            continue

        item_type = (
            match_to_enum(enum_class=ItemType, target_string=re.sub(r"\d+", "", slot.replace(" ", ""))) if item_type is None else item_type
        )
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

    file_name = (
        config.custom_file_name
        if config.custom_file_name
        else f"d4build_{class_name}_{datetime.datetime.now(tz=datetime.UTC).strftime('%Y_%m_%d_%H_%M_%S')}"
    )
    corrected_file_name = save_as_profile(file_name=file_name, profile=profile, url=url)
    if config.add_to_profiles:
        add_to_profiles(corrected_file_name)
    LOGGER.info("Finished")


def _corrections(input_str: str) -> str:
    input_str = input_str.lower()
    match input_str:
        case "max life":
            return "maximum life"
        case "total armor":
            return "armor"
    if "ranks to" in input_str or "ranks of" in input_str:
        return input_str.replace("ranks to", "to").replace("ranks of", "to")
    return input_str


def _get_item_slots(data: lxml.html.HtmlElement) -> dict[str, str]:
    result = {}
    if not (paperdoll := data.xpath(PAPERDOLL_XPATH)):
        LOGGER.error(msg := "No paperdoll found")
        raise D4BuildsException(msg)
    if not (items := paperdoll[0].xpath(PAPERDOLL_ITEM_XPATH)):
        LOGGER.error(msg := "No items found")
        raise D4BuildsException(msg)
    for item in items:
        if item.xpath(PAPERDOLL_ITEM_SLOT_XPATH):
            slot = item.xpath(PAPERDOLL_ITEM_SLOT_XPATH)[0].text
            if slot == "2H Weapon":  # This happens when a build has a weapon and no offhand
                slot = "Weapon"
            unique_name = item.xpath(PAPERDOLL_ITEM_UNIQUE_NAME_XPATH)
            result[slot] = unique_name[0].text if unique_name else ""
    return result


def _get_legendary_aspects(data: lxml.html.HtmlElement) -> list[str]:
    result = []
    if not (paperdoll := data.xpath(PAPERDOLL_XPATH)):
        # Shouldn't happen, earlier code would have thrown an exception
        return result

    aspects = paperdoll[0].xpath(PAPERDOLL_LEGENDARY_ASPECT_XPATH)
    for aspect in aspects:
        aspect_name = correct_name(aspect.text.lower().replace("aspect", "").strip())

        if aspect_name not in Dataloader().aspect_list:
            LOGGER.warning(f"Legendary aspect '{aspect_name}' that is not in our aspect data, unable to add to AspectUpgrades.")
        else:
            result.append(aspect_name)

    return result


if __name__ == "__main__":
    src.logger.setup()
    URLS = [
        "https://d4builds.gg/builds/463e7337-8fa9-491f-99a0-cbd6c65fc6f4/?var=1",
        "https://d4builds.gg/builds/b5d603bb-4442-42e8-a84d-962e6e42344c?var=0",
    ]
    for X in URLS:
        import_d4builds(url=X)
