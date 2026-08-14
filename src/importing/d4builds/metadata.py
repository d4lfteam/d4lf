import logging
import re

from lxml import etree

from src.game_data import GameCatalog, ItemRarity
from src.importing.contracts import ImportSourceError
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
from src.perception import correct_name

LOGGER = logging.getLogger(__name__)


class D4BuildsError(ImportSourceError):
    pass


def _extract_build_metadata(data: etree._Element) -> tuple[str, str, str, str]:
    class_name = "Unknown"
    if header_nodes := _xpath_elements(data, CLASS_XPATH):
        text = " ".join(etree.tostring(header_nodes[0], method="text", encoding="unicode").split()).strip()
        if text:
            class_name = get_class_name(text)

    build_header = ""
    if description_nodes := _xpath_elements(data, BUILD_DESCRIPTION_XPATH):
        build_header = " ".join(etree.tostring(description_nodes[0], method="text", encoding="unicode").split())
    elif input_nodes := _xpath_elements(data, BUILD_HEADER_INPUT_XPATH):
        build_header = str(input_nodes[0].get("value") or "").strip()
    season_number = _extract_d4builds_season_number(data=data)
    variant_name = _extract_variant_name(data=data)
    return class_name, build_header, season_number, variant_name


def _extract_variant_name(data: etree._Element) -> str:
    if variant_nodes := _xpath_elements(data, VARIANT_INPUT_XPATH):
        if variant_value := str(variant_nodes[0].get("value") or "").strip():
            return variant_value
        return " ".join(etree.tostring(variant_nodes[0], method="text", encoding="unicode").split())
    return ""


def _extract_d4builds_season_number(data: etree._Element) -> str:
    if not (season_nodes := _xpath_elements(data, SEASON_DROPDOWN_XPATH)):
        return ""
    season_text = " ".join(etree.tostring(season_nodes[0], method="text", encoding="unicode").split())
    if season_match := re.search(r"\bSeason\s+(\d+)\b", season_text, flags=re.IGNORECASE):
        return str(season_match.group(1))
    return ""


def _get_item_slots(data: etree._Element) -> dict[str, tuple[str, ItemRarity] | None]:
    result: dict[str, tuple[str, ItemRarity] | None] = {}
    if not (paperdoll := _xpath_elements(data, PAPERDOLL_XPATH)):
        LOGGER.error(msg := "No paperdoll found")
        raise D4BuildsError(msg)
    if not (items := _xpath_elements(paperdoll[0], PAPERDOLL_ITEM_XPATH)):
        LOGGER.error(msg := "No items found")
        raise D4BuildsError(msg)
    for item in items:
        if slot_nodes := _xpath_elements(item, PAPERDOLL_ITEM_SLOT_XPATH):
            slot = slot_nodes[0].text or ""
            if slot == "2H Weapon":  # This happens when a build has a weapon and no offhand
                slot = "Weapon"
            unique_name_elem = _xpath_elements(item, PAPERDOLL_ITEM_UNIQUE_NAME_XPATH)
            if unique_name_elem:
                unique_name = unique_name_elem[0].text or ""
                rarity = ItemRarity.Mythic if "mythic" in str(unique_name_elem[0].attrib) else ItemRarity.Unique
                result[slot] = (unique_name, rarity)
            else:
                result[slot] = None
    return result


def _get_legendary_aspects(data: etree._Element) -> list[str]:
    result = []
    if not (paperdoll := _xpath_elements(data, PAPERDOLL_XPATH)):
        # Shouldn't happen, earlier code would have thrown an exception
        return result

    aspects = _xpath_elements(paperdoll[0], PAPERDOLL_LEGENDARY_ASPECT_XPATH)
    for aspect in aspects:
        aspect_text = aspect.text or ""
        if not aspect_text:
            continue
        aspect_name = correct_name(aspect_text.lower().replace("aspect", "").strip())
        if aspect_name is None:
            continue

        if aspect_name not in GameCatalog().aspect_list:
            LOGGER.warning(
                f"Legendary aspect '{aspect_name}' that is not in our aspect data, unable to add to AspectUpgrades."
            )
        else:
            result.append(aspect_name)

    return result


def _get_affix_name(stat: etree._Element) -> str:
    """Bloodied attributes are saved in some special HTML that we need to remove here."""
    for span in _xpath_elements(stat, "./span"):
        affix_name = " ".join(etree.tostring(span, method="text", encoding="unicode").split())
        if affix_name:
            return affix_name
    return ""


def _xpath_elements(data: etree._Element, xpath: str) -> list[etree._Element]:
    nodes = data.xpath(xpath)
    if not isinstance(nodes, list):
        return []
    return [node for node in nodes if isinstance(node, etree._Element)]


__all__ = [name for name in globals() if not name.startswith("__")]
