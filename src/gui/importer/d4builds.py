import logging
import re
import time
from typing import TYPE_CHECKING

import lxml.html
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

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
    get_class_name,
    match_to_enum,
    retry_importer,
    save_as_profile,
    update_mingreateraffixcount,
)
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.paragon_export import build_paragon_profile_payload, extract_d4builds_paragon_steps
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import WEAPON_TYPES, ItemType
from src.item.descr.text import clean_str, closest_match
from src.scripts import correct_name

if TYPE_CHECKING:
    from selenium.webdriver.chromium.webdriver import ChromiumDriver

LOGGER = logging.getLogger(__name__)

BASE_URL = "https://d4builds.gg/builds"
BUILD_OVERVIEW_XPATH = "//*[@class='builder__stats__list']"
CLASS_XPATH = "//*[contains(@class, 'builder__header__name')]"
CLASS_ICON_XPATH = "//*[contains(@class, 'builder__header__icon')]"
BUILD_DESCRIPTION_XPATH = "//*[contains(@class, 'builder__header__description')]"
BUILD_HEADER_INPUT_XPATH = "//*[contains(@class, 'builder__header__input')]"
VARIANT_INPUT_XPATH = "//*[contains(@class, 'builder__variant__input')]"
SEASON_DROPDOWN_XPATH = (
    "//*[contains(@class, 'builder__gear')]/*[contains(@class, 'builder__dropdown__wrapper')]"
    "//*[contains(@class, 'dropdown__button') and starts-with(normalize-space(), 'Season ')]"
)
ITEM_GROUP_XPATH = ".//*[contains(@class, 'builder__stats__group')]"
ITEM_SLOT_XPATH = ".//*[contains(@class, 'builder__stats__slot')]"
ITEM_STATS_XPATH = ".//*[contains(@class, 'dropdown__button__wrapper')]"
GA_XPATH = ".//*[contains(@class, 'greater__affix__button--filled')]"
PAPERDOLL_ITEM_SLOT_XPATH = ".//*[contains(@class, 'builder__gear__slot')]"
PAPERDOLL_ITEM_UNIQUE_NAME_XPATH = ".//*[contains(@class, 'builder__gear__name--')]"
PAPERDOLL_ITEM_XPATH = ".//*[contains(@class, 'builder__gear__item') and not(contains(@class, 'disabled'))]"
PAPERDOLL_LEGENDARY_ASPECT_XPATH = (
    "//*[@class='builder__gear__name' and not(contains(@class, 'builder__gear__name--'))]"
)
PAPERDOLL_XPATH = "//*[contains(@class, 'builder__gear__items')]"
TEMPERING_ICON_XPATH = ".//*[contains(@src, 'tempering_02.png')]"
SANCTIFIED_ICON_XPATH = ".//*[contains(@src, 'sanctified_icon.png')]"
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
    time.sleep(
        5
    )  # super hacky but I didn't find anything else. The page is not fully loaded when the above wait is done
    data = lxml.html.fromstring(driver.page_source)
    class_name, build_header, variant_name = _extract_build_metadata(data=data, page_title=driver.title.strip())
    build_name = build_header or class_name
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

        if slot_to_unique_name_map[slot]:
            unique_model = UniqueModel()
            unique_name = slot_to_unique_name_map[slot]
            try:
                unique_model.aspect = AspectUniqueFilterModel(name=unique_name)
                # We just can't trust their data well enough so removing this just like the other importers.
                # unique_model.affix = [AffixFilterModel(name=x.name) for x in affixes]
                unique_filters.append(unique_model)
            except Exception:
                LOGGER.exception(
                    f"Unexpected error importing unique {unique_name}, please report a bug and include a link to the build you were trying to import."
                )
            continue

        is_weapon = "weapon" in slot.lower()
        for stat in stats:
            if stat.xpath(TEMPERING_ICON_XPATH) or stat.xpath(SANCTIFIED_ICON_XPATH):
                continue
            if "filled" not in stat.xpath("../..")[0].attrib["class"]:
                continue
            affix_name = _get_affix_name(stat)
            if not affix_name:
                LOGGER.warning(f"Slot {slot} is missing an affix, skipping import of that affix.")
                continue
            if is_weapon and (x := fix_weapon_type(input_str=affix_name)) is not None:
                item_type = x
                continue
            if (
                "offhand" in slot.lower()
                and (x := fix_offhand_type(input_str=affix_name, class_str=class_name)) is not None
            ):
                item_type = x
                if any(
                    substring in affix_name.lower() for substring in ["focus", "offhand", "shield", "totem"]
                ):  # special line indicating the item type
                    continue
            affix_obj = Affix(
                name=closest_match(clean_str(_corrections(input_str=affix_name)), Dataloader().affix_dict)
            )
            if affix_obj.name is None:
                LOGGER.error(f"Couldn't match {affix_name=}")
                continue
            if config.import_greater_affixes and stat.xpath("../../../..")[0].xpath(GA_XPATH):
                affix_obj.type = AffixType.greater
            if (
                "ring" in slot.lower()
                and any(substring in affix_name.lower() for substring in ["resistance"])
                and not any(
                    substring in affix_name.lower() for substring in ["elements"]
                )  # Exclude resistance to all elements
            ) or (
                "boots" in slot.lower()
                and any(substring in affix_name.lower() for substring in ["max evade charges", "attacks reduce"])
            ):
                inherents.append(affix_obj)
            else:
                affixes.append(affix_obj)

        if not affixes:
            continue

        item_type = (
            match_to_enum(enum_class=ItemType, target_string=re.sub(r"\d+", "", slot.replace(" ", "")))
            if item_type is None
            else item_type
        )
        if item_type is None:
            if is_weapon:
                LOGGER.warning(
                    f"Couldn't find an item_type for weapon slot {slot}, defaulting to all weapon types instead."
                )
                item_filter.itemType = WEAPON_TYPES
            else:
                item_filter.itemType = []
                LOGGER.warning(f"Couldn't match item_type: {slot}. Please edit manually")
        else:
            item_filter.itemType = [item_type]
        item_filter.affixPool = [
            AffixFilterCountModel(
                count=[AffixFilterModel(name=x.name, want_greater=x.type == AffixType.greater) for x in affixes],
                minCount=3,
            )
        ]
        item_filter.minPower = 100
        update_mingreateraffixcount(item_filter, config.require_greater_affixes)
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

    file_name = config.custom_file_name or build_default_profile_file_name(
        url=url, class_name=class_name, build_header=build_header, variant_name=variant_name
    )

    # Optionally embed Paragon data into the profile model before saving
    if config.export_paragon:
        steps = extract_d4builds_paragon_steps(driver, class_name=class_name)
        if steps:
            profile.Paragon = build_paragon_profile_payload(
                build_name=build_name, source_url=url, paragon_boards_list=steps
            )
        else:
            LOGGER.warning("Paragon export enabled, but no paragon data was found on this D4Builds page.")

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
    if "ranks to" in input_str or "ranks of" in input_str or "ranks" in input_str:
        return input_str.replace("ranks to", "to").replace("ranks of", "to").replace("ranks", "to")
    return input_str


def _extract_build_metadata(data: lxml.html.HtmlElement, page_title: str) -> tuple[str, str, str]:
    class_name = _extract_class_name(data=data)
    build_header = _extract_build_header(data=data, class_name=class_name, page_title=page_title)
    season_number = _extract_d4builds_season_number(data=data)
    build_header = _apply_d4builds_season_to_build_header(build_header=build_header, season_number=season_number)
    variant_name = _extract_variant_name(data=data)
    return class_name, build_header, variant_name


def _extract_class_name(data: lxml.html.HtmlElement) -> str:
    for icon in data.xpath(CLASS_ICON_XPATH):
        class_name = get_class_name(f"{icon.get('class', '')} {icon.get('alt', '')}")
        if class_name != "Unknown":
            return class_name

    if (elem := data.xpath(CLASS_XPATH + "/*")) or (elem := data.xpath(CLASS_XPATH)):
        class_name = get_class_name(f"{elem[0].tail} {elem[0].text}")
        if class_name != "Unknown":
            return class_name
    return "Unknown"


def _extract_build_header(data: lxml.html.HtmlElement, class_name: str, page_title: str) -> str:
    header_name = ""
    if header_nodes := data.xpath(CLASS_XPATH):
        header_name = _get_header_name_text(header_nodes[0])

    description = ""
    if description_nodes := data.xpath(BUILD_DESCRIPTION_XPATH):
        description = " ".join(description_nodes[0].text_content().split())

    for candidate in (header_name, description, page_title.strip()):
        if candidate and not _is_generic_build_header(candidate, class_name):
            return candidate
    return description or header_name or page_title.strip()


def _get_header_name_text(header_node: lxml.html.HtmlElement) -> str:
    if input_nodes := header_node.xpath(BUILD_HEADER_INPUT_XPATH):
        input_value = str(input_nodes[0].get("value") or "").strip()
        if input_value:
            return input_value
    return " ".join(header_node.text_content().split())


def _is_generic_build_header(build_header: str, class_name: str) -> bool:
    normalized_header = " ".join(build_header.split()).casefold()
    normalized_class_name = class_name.casefold()
    generic_headers = {
        f"{normalized_class_name} build",
        f"diablo 4 {normalized_class_name} build",
        f"diablo 4 {normalized_class_name} build · d4 builds",
    }
    return normalized_header in generic_headers or normalized_header.endswith("build guide - diablo 4")


def _extract_variant_name(data: lxml.html.HtmlElement) -> str:
    if variant_nodes := data.xpath(VARIANT_INPUT_XPATH):
        if variant_value := str(variant_nodes[0].get("value") or "").strip():
            return variant_value
        return " ".join(variant_nodes[0].text_content().split())
    return ""


def _extract_d4builds_season_number(data: lxml.html.HtmlElement) -> str:
    if season_nodes := data.xpath(SEASON_DROPDOWN_XPATH):
        season_text = " ".join(season_nodes[0].text_content().split())
        if season_match := re.search(r"\bSeason\s+(\d+)\b", season_text, flags=re.IGNORECASE):
            return season_match.group(1)

    top_level_text = " ".join(data.text_content().split()).split("Active Runes", 1)[0]
    if season_match := re.search(r"\bSeason\s+(\d+)\b", top_level_text, flags=re.IGNORECASE):
        return season_match.group(1)
    return ""


def _apply_d4builds_season_to_build_header(build_header: str, season_number: str) -> str:
    if not build_header:
        return build_header
    if not season_number:
        if (season_match := re.search(r"\bSeason\s+(\d+)\b", build_header, flags=re.IGNORECASE)) or (
            season_match := re.search(r"\bS(\d+)\b", build_header, flags=re.IGNORECASE)
        ):
            season_number = season_match.group(1)
        else:
            return build_header
    normalized_build_header = re.sub(r"\(\s*(?:S\d+|Season\s+\d+)\s*\)", "", build_header, count=1, flags=re.IGNORECASE)
    normalized_build_header = re.sub(
        r"\b(?:S\d+|Season\s+\d+)\b", "", normalized_build_header, count=1, flags=re.IGNORECASE
    )
    normalized_build_header = re.sub(r"\(\s*\)", "", normalized_build_header)
    normalized_build_header = re.sub(r"\s+", " ", normalized_build_header).strip(" -_:")
    return f"S{season_number} {normalized_build_header}".strip()


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
            LOGGER.warning(
                f"Legendary aspect '{aspect_name}' that is not in our aspect data, unable to add to AspectUpgrades."
            )
        else:
            result.append(aspect_name)

    return result


def _get_affix_name(stat: lxml.html.HtmlElement) -> str:
    """Bloodied attributes are saved in some special HTML that we need to remove here."""
    for span in stat.xpath("./span"):
        affix_name = " ".join(span.text_content().split())
        if affix_name:
            return affix_name
    return ""


if __name__ == "__main__":
    src.logger.setup()
    URLS = ["https://d4builds.gg/builds/e3aab60e-15a0-47ee-99ec-648788901104/?var=1"]
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
        import_d4builds(config)
