import logging
import re
from typing import TYPE_CHECKING

from src.importing.d4builds.constants import (
    BUILD_DESCRIPTION_XPATH,
    BUILD_HEADER_INPUT_XPATH,
    CLASS_XPATH,
    PAPERDOLL_ITEM_SLOT_XPATH,
    PAPERDOLL_ITEM_UNIQUE_NAME_XPATH,
    PAPERDOLL_ITEM_XPATH,
    PAPERDOLL_LEGENDARY_ASPECT_XPATH,
    PAPERDOLL_XPATH,
    SEASON_DROPDOWN_XPATH,
    VARIANT_INPUT_XPATH,
)
from src.importing.filters import get_class_name
from src.item import Dataloader, ItemRarity
from src.perception import correct_name

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    import lxml.html


class D4BuildsError(Exception):
    pass


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


__all__ = [name for name in globals() if not name.startswith("__")]
