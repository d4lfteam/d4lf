import logging
from typing import TYPE_CHECKING

import lxml.html
from selenium.webdriver.common.by import By

from src.importing._filters import (
    affix_dict_for_item_type,
    create_seal_charm_filter,
    fix_weapon_type,
    match_set_aware_seal_affix,
)
from src.importing._web import hover_and_get_tooltip_html
from src.item import Affix, ItemType
from src.item.descr.text import clean_str, closest_match
from src.profiles import CharmFilterModel, SealFilterModel
from src.scripts import correct_name

from .constants import (
    ACTIVE_CHARM_CSS,
    ACTIVE_SEAL_CSS,
    CHARM_TOOLTIP_CSS,
    CHARM_TOOLTIP_SET_NAME_XPATH,
    CHARM_TOOLTIP_UNIQUE_XPATH,
    CHARM_TOOLTIP_VALUE_XPATH,
    PAPERDOLL_GEAR_ICON_CSS,
    PAPERDOLL_ITEM_SLOT_CSS,
    PAPERDOLL_WEAPON_ITEM_CSS,
    SEAL_TOOLTIP_CSS,
    SEAL_TOOLTIP_VALUE_XPATH,
    UNIQUE_TOOLTIP_CSS,
    UNIQUE_TOOLTIP_SLOT_XPATH,
)

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement

    from src.importing.contracts import ImportRequest

LOGGER = logging.getLogger(__name__)


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


__all__ = [name for name in globals() if not name.startswith("__")]


def _extract_d4builds_seal_charm_filters(
    driver: WebDriver, request: ImportRequest
) -> tuple[list[CharmFilterModel], list[SealFilterModel]]:
    charm_filters = []
    seal_filters = []
    set_names = []

    for _, charm_element in enumerate(driver.find_elements(By.CSS_SELECTOR, ACTIVE_CHARM_CSS)):
        tooltip_html = hover_and_get_tooltip_html(driver=driver, element=charm_element, tooltip_css=CHARM_TOOLTIP_CSS)
        charm_filter, set_name = _create_charm_filter_from_tooltip_html(
            tooltip_html=tooltip_html, require_gas=request.options.require_greater_affixes
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
            tooltip_html=tooltip_html,
            require_gas=request.options.require_greater_affixes,
            guessed_set_name=guessed_set_name,
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


__all__ = [name for name in globals() if not name.startswith("__")]
