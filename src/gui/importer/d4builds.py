import logging
import re
import time
from typing import TYPE_CHECKING

import lxml.html
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

import src.logger
from src.dataloader import Dataloader
from src.gui.importer.gui_common import (
    affix_dict_for_item_type,
    create_item_affix_pool,
    create_seal_charm_filter,
    fix_offhand_type,
    fix_weapon_type,
    get_class_name,
    hover_and_get_tooltip_html,
    is_unique_like_rarity,
    match_set_aware_seal_affix,
    match_to_enum,
    retry_importer,
    update_mingreateraffixcount,
    weapon_slot_name_hint,
)
from src.gui.importer.import_pipeline import ExtractedBuild, ImportPipeline, StaticBuildGuideAdapter, Variant
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.paragon_export import extract_d4builds_paragon_steps
from src.item import WEAPON_TYPES, Affix, AffixType, ItemRarity, ItemType
from src.item.descr.text import clean_str, closest_match
from src.profiles import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    CharmFilterModel,
    ItemFilterModel,
    SealFilterModel,
)
from src.scripts import correct_name

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement


LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True

ACTIVE_CHARM_CSS = ".builder__charm.active"
ACTIVE_SEAL_CSS = ".builder__seal.active"
BASE_URL = "https://d4builds.gg/builds"
BUILD_DESCRIPTION_XPATH = "//*[contains(@class, 'builder__header__description')]"
BUILD_HEADER_INPUT_XPATH = "//*[contains(@class, 'builder__header__input')]"
BUILD_OVERVIEW_XPATH = "//*[@class='builder__stats__list']"
CHARM_TOOLTIP_CSS = "[data-tippy-root] .charm__tooltip"
CHARM_TOOLTIP_SET_NAME_XPATH = ".//*[contains(@class, 'charm__tooltip__set__name')]"
CHARM_TOOLTIP_UNIQUE_XPATH = ".//*[contains(@class, 'charm__tooltip__name--unique')]"
CHARM_TOOLTIP_VALUE_XPATH = (
    ".//*[contains(@class, 'charm__tooltip__values')]//*[contains(@class, 'charm__tooltip__value')]"
)
CLASS_XPATH = "//*[contains(@class, 'builder__header__name')]"
GA_XPATH = ".//*[contains(@class, 'greater__affix__button--filled')]"
ITEM_GROUP_XPATH = ".//*[contains(@class, 'builder__stats__group')]"
ITEM_SLOT_XPATH = ".//*[contains(@class, 'builder__stats__slot')]"
ITEM_STATS_XPATH = ".//*[contains(@class, 'dropdown__button__wrapper')]"
PAPERDOLL_GEAR_ICON_CSS = ".builder__gear__icon"
PAPERDOLL_ITEM_SLOT_CSS = ".builder__gear__slot"
PAPERDOLL_ITEM_SLOT_XPATH = ".//*[contains(@class, 'builder__gear__slot')]"
PAPERDOLL_ITEM_UNIQUE_NAME_XPATH = ".//*[contains(@class, 'builder__gear__name--')]"
PAPERDOLL_ITEM_XPATH = ".//*[contains(@class, 'builder__gear__item') and not(contains(@class, 'disabled'))]"
PAPERDOLL_LEGENDARY_ASPECT_XPATH = (
    "//*[@class='builder__gear__name' and not(contains(@class, 'builder__gear__name--'))]"
)
PAPERDOLL_WEAPON_ITEM_CSS = ".builder__gear__item.weapon:not(.disabled)"
PAPERDOLL_XPATH = "//*[contains(@class, 'builder__gear__items')]"
SANCTIFIED_ICON_XPATH = ".//*[contains(@src, 'sanctified_icon.png')]"
SEAL_TOOLTIP_CSS = "[data-tippy-root] .seal__tooltip"
SEAL_TOOLTIP_VALUE_XPATH = ".//*[contains(@class, 'seal__tooltip__value__text')]"
SEASON_DROPDOWN_XPATH = "//*[contains(@class, 'builder__gear')]/*[contains(@class, 'builder__dropdown__wrapper')]//*[contains(@class, 'dropdown__button') and starts-with(normalize-space(), 'Season ')]"
TEMPERING_ICON_XPATH = ".//*[contains(@src, 'tempering_02.png')]"
UNIQUE_ICON_XPATH = ".//*[contains(@src, '/Uniques/')]"
UNIQUE_TOOLTIP_CSS = "[data-tippy-root] .unique__tooltip"
UNIQUE_TOOLTIP_SLOT_XPATH = ".//*[contains(@class, 'unique__tooltip__slot')]"
VARIANT_INPUT_XPATH = "//*[contains(@class, 'builder__variant__input')]"


class D4BuildsError(Exception):
    pass


@retry_importer(inject_webdriver=True)
def import_d4builds(config: ImportConfig, driver: WebDriver | None = None) -> None:
    if driver is None:
        msg = "A Selenium WebDriver is required for D4Builds imports"
        raise RuntimeError(msg)
    url = config.url.strip().replace("\n", "")
    if BASE_URL not in url:
        LOGGER.error("Invalid url, please use a d4builds url")
        return
    LOGGER.info(f"Loading {url}")
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(ec.presence_of_element_located((By.XPATH, BUILD_OVERVIEW_XPATH)))
    wait.until(ec.presence_of_element_located((By.XPATH, PAPERDOLL_XPATH)))
    time.sleep(
        5
    )  # super hacky but I didn't find anything else. The page is not fully loaded when the above wait is done
    data = lxml.html.fromstring(driver.page_source)
    class_name, build_header, season_number, variant_name = _extract_build_metadata(data=data)
    if not (items := data.xpath(BUILD_OVERVIEW_XPATH)):
        LOGGER.error(msg := "No items found")
        raise D4BuildsError(msg)
    slot_to_unique_name_map = _get_item_slots(data=data)
    weapon_paperdoll_icons = _get_weapon_paperdoll_icons(driver=driver)
    finished_filters: list[ItemFilterModel] = []
    finished_filter_name_hints: list[str | None] = []
    charm_filters, seal_filters = _extract_d4builds_seal_charm_filters(driver=driver, config=config)
    aspect_upgrade_filters = _get_legendary_aspects(data=data)
    for item in items[0]:
        item_filter = ItemFilterModel()
        if not (slot := item.xpath(ITEM_SLOT_XPATH)[1].tail):
            LOGGER.error("No item_type found")
            continue
        if slot not in slot_to_unique_name_map:
            LOGGER.warning(f"Empty slots are not supported. Skipping: {slot}")
            continue

        stats = item.xpath(ITEM_STATS_XPATH)
        if not stats:
            LOGGER.error(f"No stats found for {slot=}")
            continue

        item_type = None
        rarity = None
        affixes = []
        inherents = []

        unique_item = slot_to_unique_name_map[slot]
        if unique_item is not None:
            unique_name, rarity = unique_item
            try:
                item_filter.unique_aspect = [AspectUniqueFilterModel(name=unique_name)]
            except Exception:
                LOGGER.exception(
                    f"Unexpected error adding unique aspect for {unique_name}, please report a bug and include a link to the build you were trying to import."
                )
        is_unique_like = is_unique_like_rarity(rarity)

        is_weapon = "weapon" in slot.lower()
        affix_dict = affix_dict_for_item_type(item_type=item_type)
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
            affix_obj = Affix(name=closest_match(clean_str(_corrections(input_str=affix_name)), affix_dict))
            if affix_obj.name is None:
                LOGGER.error(f"Couldn't match {affix_name=}")
                continue
            if config.import_greater_affixes and stat.xpath("../../../..")[0].xpath(GA_XPATH):
                affix_obj.type = AffixType.greater
            affixes.append(affix_obj)

        item_type = (
            match_to_enum(enum_class=ItemType, target_string=re.sub(r"\d+", "", slot.replace(" ", "")))
            if item_type is None
            else item_type
        )

        if not affixes and not item_filter.unique_aspect:
            continue

        if item_type is None and is_weapon and (icon := weapon_paperdoll_icons.get(slot)) is not None:
            item_type = _get_weapon_type_from_paperdoll_tooltip(driver=driver, icon=icon)

        if item_type is None:
            if is_weapon:
                LOGGER.warning(
                    f"Couldn't find an item_type for weapon slot {slot}, defaulting to all weapon types instead."
                )
                item_filter.item_type = WEAPON_TYPES
            else:
                item_filter.item_type = []
                LOGGER.warning(f"Couldn't match item_type: {slot}. Please edit manually")
        else:
            item_filter.item_type = [item_type]

        if affixes:
            item_filter.affix_pool = create_item_affix_pool(affixes=affixes, unique_like=is_unique_like)
            update_mingreateraffixcount(item_filter, config.require_greater_affixes)
            if inherents:
                item_filter.inherent_pool = [
                    AffixFilterCountModel(count=[AffixFilterModel(name=x.name) for x in inherents])
                ]
        item_filter.min_power = 100
        finished_filters.append(item_filter)
        finished_filter_name_hints.append(weapon_slot_name_hint(item_filter, slot))
    ImportPipeline.run(
        adapter=StaticBuildGuideAdapter(
            url=url,
            build=ExtractedBuild(
                source_name="d4builds",
                class_name=class_name,
                build_header=build_header,
                season_number=season_number,
                variants=[
                    Variant(
                        name=variant_name,
                        affix_filters=finished_filters,
                        affix_filter_name_hints=finished_filter_name_hints,
                        charm_filters=charm_filters,
                        seal_filters=seal_filters,
                        aspect_upgrade_filters=aspect_upgrade_filters,
                        paragon_steps=extract_d4builds_paragon_steps(driver, class_name=class_name),
                        paragon_build_name=build_header or class_name,
                    )
                ],
            ),
        ),
        config=config,
    )


def _corrections(input_str: str) -> str:
    input_str = input_str.lower()
    match input_str:
        case "max life":
            return "maximum life"
        case "total armor":
            return "armor"
    if "ranks to" in input_str or "ranks of" in input_str or "ranks" in input_str:
        return input_str.replace("ranks to", "to").replace("ranks of", "to").replace("ranks", "to")
    if "charm slot" in input_str:
        return "charm slot"
    return input_str


def _weapon_type_from_unique_tooltip_html(tooltip_html: str) -> ItemType | None:
    tooltip = _tooltip_element(tooltip_html)
    if tooltip is None:
        return None
    slot_text = _first_text(tooltip=tooltip, xpath=UNIQUE_TOOLTIP_SLOT_XPATH)
    if not slot_text:
        return None
    return fix_weapon_type(input_str=slot_text)


def _get_weapon_paperdoll_icons(driver: WebDriver) -> dict[str, WebElement]:
    """Map weapon slot name to its paperdoll gear icon element, without hovering anything.

    Hovering (to read the tooltip) is comparatively slow, so callers should only hover the icon for a
    slot once they've confirmed the affix bullets alone couldn't resolve that slot's item_type.
    """
    result = {}
    for item in driver.find_elements(By.CSS_SELECTOR, PAPERDOLL_WEAPON_ITEM_CSS):
        slot_elements = item.find_elements(By.CSS_SELECTOR, PAPERDOLL_ITEM_SLOT_CSS)
        icon_elements = item.find_elements(By.CSS_SELECTOR, PAPERDOLL_GEAR_ICON_CSS)
        if not slot_elements or not icon_elements:
            continue
        slot = slot_elements[0].text
        if slot == "2H Weapon":  # This happens when a build has a weapon and no offhand
            slot = "Weapon"
        result[slot] = icon_elements[0]
    return result


def _get_weapon_type_from_paperdoll_tooltip(driver: WebDriver, icon: WebElement) -> ItemType | None:
    """Hover a unique/mythic weapon paperdoll icon to read its type from the tooltip.

    D4Builds only reveals a weapon's type this way for unique/mythic items; generic legendary weapons
    (aspect only) show an aspect tooltip with no type info, so this returns None for those.
    """
    tooltip_html = hover_and_get_tooltip_html(
        driver=driver, element=icon, tooltip_css=UNIQUE_TOOLTIP_CSS, warn_on_timeout=False
    )
    return _weapon_type_from_unique_tooltip_html(tooltip_html)


def _extract_d4builds_seal_charm_filters(
    driver: WebDriver, config: ImportConfig
) -> tuple[list[CharmFilterModel], list[SealFilterModel]]:
    charm_filters = []
    seal_filters = []
    set_names = []

    for _, charm_element in enumerate(driver.find_elements(By.CSS_SELECTOR, ACTIVE_CHARM_CSS)):
        tooltip_html = hover_and_get_tooltip_html(driver=driver, element=charm_element, tooltip_css=CHARM_TOOLTIP_CSS)
        charm_filter, set_name = _create_charm_filter_from_tooltip_html(
            tooltip_html=tooltip_html, require_gas=config.require_greater_affixes
        )
        if charm_filter is not None:
            charm_filters.append(charm_filter)
        if set_name and set_name not in set_names:
            set_names.append(set_name)

    if len(set_names) > 1:
        LOGGER.warning(
            "Found multiple charm sets in D4Builds build (%s); using %s for set-specific seal affixes.",
            ", ".join(set_names),
            set_names[0],
        )
    guessed_set_name = set_names[0] if set_names else None

    for seal_element in driver.find_elements(By.CSS_SELECTOR, ACTIVE_SEAL_CSS):
        tooltip_html = hover_and_get_tooltip_html(driver=driver, element=seal_element, tooltip_css=SEAL_TOOLTIP_CSS)
        seal_filter = _create_seal_filter_from_tooltip_html(
            tooltip_html=tooltip_html, require_gas=config.require_greater_affixes, guessed_set_name=guessed_set_name
        )
        if seal_filter is not None:
            seal_filters.append(seal_filter)

    return charm_filters, seal_filters


def _create_seal_filter_from_tooltip_html(
    tooltip_html: str, require_gas: bool, guessed_set_name: str | None = None
) -> SealFilterModel | None:
    affixes = _affixes_from_tooltip_values(
        texts=_tooltip_texts(tooltip_html=tooltip_html, value_xpath=SEAL_TOOLTIP_VALUE_XPATH),
        item_type=ItemType.HoradricSeal,
        guessed_set_name=guessed_set_name,
    )
    if not affixes:
        return None
    return create_seal_charm_filter(affixes=affixes, require_gas=require_gas, model_type=SealFilterModel)


def _create_charm_filter_from_tooltip_html(
    tooltip_html: str, require_gas: bool
) -> tuple[CharmFilterModel | None, str | None]:
    tooltip = _tooltip_element(tooltip_html)
    if tooltip is None:
        return None, None

    set_name = correct_name(_first_text(tooltip=tooltip, xpath=CHARM_TOOLTIP_SET_NAME_XPATH))
    unique_name = correct_name(_first_text(tooltip=tooltip, xpath=CHARM_TOOLTIP_UNIQUE_XPATH))
    affixes = _affixes_from_tooltip_values(
        texts=_texts_from_nodes(tooltip.xpath(CHARM_TOOLTIP_VALUE_XPATH)), item_type=ItemType.Charm
    )

    if not affixes and not unique_name and not set_name:
        return None, None

    return (
        create_seal_charm_filter(
            affixes=affixes,
            require_gas=require_gas,
            model_type=CharmFilterModel,
            unique_name=unique_name,
            set_name=set_name,
        ),
        set_name,
    )


def _affixes_from_tooltip_values(
    texts: list[str], item_type: ItemType, guessed_set_name: str | None = None
) -> list[Affix]:
    affixes = []
    for text in texts:
        affix_name = _match_d4builds_tooltip_affix(text=text, item_type=item_type, guessed_set_name=guessed_set_name)
        if affix_name is None:
            LOGGER.error(f"Couldn't match D4Builds seal/charm tooltip affix {text=}")
            continue
        affixes.append(Affix(name=affix_name))
    return affixes


def _match_d4builds_tooltip_affix(text: str, item_type: ItemType, guessed_set_name: str | None = None) -> str | None:
    stat_clean = clean_str(_corrections(input_str=text))
    affix_dict = affix_dict_for_item_type(item_type=item_type)

    if (
        item_type == ItemType.HoradricSeal
        and guessed_set_name
        and (
            matched_name := match_set_aware_seal_affix(
                stat_clean=stat_clean, affix_dict=affix_dict, guessed_set_name=guessed_set_name
            )
        )
    ):
        return matched_name

    return closest_match(stat_clean, affix_dict)


def _tooltip_texts(tooltip_html: str, value_xpath: str) -> list[str]:
    tooltip = _tooltip_element(tooltip_html)
    return [] if tooltip is None else _texts_from_nodes(tooltip.xpath(value_xpath))


def _tooltip_element(tooltip_html: str) -> lxml.html.HtmlElement | None:
    if not tooltip_html:
        return None
    return lxml.html.fromstring(tooltip_html)


def _texts_from_nodes(nodes: list[lxml.html.HtmlElement]) -> list[str]:
    return [text for node in nodes if (text := " ".join(node.text_content().split()))]


def _first_text(tooltip: lxml.html.HtmlElement, xpath: str) -> str:
    return _texts_from_nodes(tooltip.xpath(xpath))[0] if tooltip.xpath(xpath) else ""


def _extract_build_metadata(data: lxml.html.HtmlElement) -> tuple[str, str, str, str]:
    class_name = "Unknown"
    if header_nodes := data.xpath(CLASS_XPATH):
        text = " ".join(header_nodes[0].text_content().split()).strip()
        if text:
            class_name = get_class_name(text)

    build_header = ""
    if description_nodes := data.xpath(BUILD_DESCRIPTION_XPATH):
        build_header = " ".join(description_nodes[0].text_content().split())
    elif input_nodes := data.xpath(BUILD_HEADER_INPUT_XPATH):
        build_header = str(input_nodes[0].get("value") or "").strip()
    season_number = _extract_d4builds_season_number(data=data)
    variant_name = _extract_variant_name(data=data)
    return class_name, build_header, season_number, variant_name


def _extract_variant_name(data: lxml.html.HtmlElement) -> str:
    if variant_nodes := data.xpath(VARIANT_INPUT_XPATH):
        if variant_value := str(variant_nodes[0].get("value") or "").strip():
            return variant_value
        return " ".join(variant_nodes[0].text_content().split())
    return ""


def _extract_d4builds_season_number(data: lxml.html.HtmlElement) -> str:
    if not (season_nodes := data.xpath(SEASON_DROPDOWN_XPATH)):
        return ""
    season_text = " ".join(season_nodes[0].text_content().split())
    if season_match := re.search(r"\bSeason\s+(\d+)\b", season_text, flags=re.IGNORECASE):
        return season_match.group(1)
    return ""


def _get_item_slots(data: lxml.html.HtmlElement) -> dict[str, tuple[str, ItemRarity] | None]:
    result = {}
    if not (paperdoll := data.xpath(PAPERDOLL_XPATH)):
        LOGGER.error(msg := "No paperdoll found")
        raise D4BuildsError(msg)
    if not (items := paperdoll[0].xpath(PAPERDOLL_ITEM_XPATH)):
        LOGGER.error(msg := "No items found")
        raise D4BuildsError(msg)
    for item in items:
        if item.xpath(PAPERDOLL_ITEM_SLOT_XPATH):
            slot = item.xpath(PAPERDOLL_ITEM_SLOT_XPATH)[0].text
            if slot == "2H Weapon":  # This happens when a build has a weapon and no offhand
                slot = "Weapon"
            unique_name_elem = item.xpath(PAPERDOLL_ITEM_UNIQUE_NAME_XPATH)
            if unique_name_elem:
                unique_name = unique_name_elem[0].text
                rarity = ItemRarity.Mythic if "mythic" in str(unique_name_elem[0].attrib) else ItemRarity.Unique
                result[slot] = (unique_name, rarity)
            else:
                result[slot] = None
    return result


def _get_legendary_aspects(data: lxml.html.HtmlElement) -> list[str]:
    result = []
    if not (paperdoll := data.xpath(PAPERDOLL_XPATH)):
        # Shouldn't happen, earlier code would have thrown an exception
        return result

    aspects = paperdoll[0].xpath(PAPERDOLL_LEGENDARY_ASPECT_XPATH)
    for aspect in aspects:
        aspect_text = aspect.text
        if not aspect_text:
            continue
        aspect_name = correct_name(aspect_text.lower().replace("aspect", "").strip())
        if aspect_name is None:
            continue

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
    from src.gui.importer.gui_common import setup_webdriver

    driver = setup_webdriver()

    URLS = ["https://d4builds.gg/builds/penetrating-shot-rogue-endgame/?var=0"]
    for X in URLS:
        config = ImportConfig(
            url=X,
            import_aspect_upgrades=True,
            add_to_profiles=False,
            import_greater_affixes=True,
            require_greater_affixes=True,
            export_paragon=True,
            custom_file_name=None,
        )
        import_d4builds(config, driver)
