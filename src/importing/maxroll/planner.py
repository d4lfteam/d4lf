import json
import logging
import re
from typing import TYPE_CHECKING

import lxml.html

from src.game_data import ItemType
from src.importing.contracts import ImportSourceError
from src.importing.conversion import as_string_keyed_mapping as _as_mapping
from src.importing.filters import fix_offhand_type, fix_weapon_type, match_to_enum
from src.importing.maxroll.constants import (
    BUILD_SCRIPT_PREFIX,
    PLANNER_API_BASE_URL,
    PLANNER_API_REGEX,
    PLANNER_BASE_URL,
    SCRIPT_XPATH,
)
from src.importing.web import get_with_retry
from src.perception import correct_name

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

LOGGER = logging.getLogger(__name__)


class MaxrollError(ImportSourceError):
    pass


def _find_legendary_aspect(
    mapping_data: Mapping[str, object], legendary_aspect: Mapping[str, object] | list[object]
) -> str | None:
    if not legendary_aspect:
        return None

    if isinstance(legendary_aspect, list):
        if not legendary_aspect:
            return None
        first_aspect = legendary_aspect[0]
        if not isinstance(first_aspect, dict):
            return None
        aspect_data = _as_mapping(first_aspect)
    else:
        aspect_data = _as_mapping(legendary_aspect)

    aspect_id = aspect_data.get("nid")
    for raw_affix in _as_mapping(mapping_data.get("affixes")).values():
        affix = _as_mapping(raw_affix)
        if affix.get("id") != aspect_id:
            continue

        prefix = affix.get("prefix")
        if isinstance(prefix, str):
            return correct_name(prefix)
        suffix = affix.get("suffix")
        if isinstance(suffix, str):
            return correct_name(suffix)
        return None

    return None


def _attr_desc_special_handling(affix_id: int | str) -> str:
    match affix_id:
        case 2609197:
            return "charm slot"
        # case 1014505 | 2051010:
        #     return "evade grants movement speed for second"
        # case 2568489:
        #     return "hunger increased reputation from kill streaks"
        # case 2568491:
        #     return "hunger increased experience from kill streaks"
        # case 2057810:
        #     return "damage reduction from bleeding enemies"
        # case 2067844:
        #     return "maximum poison resistance"
        # case 2037914:
        #     return "subterfuge cooldown reduction"
        # case 2123788:
        #     return "chance for core skills to hit twice"
        # case 2119054:
        #     return "chance for basic skills to deal double damage"
        # case 2119058:
        #     return "basic lucky hit chance"
        # case 2052125:
        #     return "non-physical damage"
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


def _find_item_type(mapping_data: Mapping[str, Mapping[str, str]], value: str, class_name: str = "") -> ItemType | None:
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


def _extract_planner_url_and_id_from_planner(url: str) -> tuple[str, int, bool]:
    planner_suffix = url.split(PLANNER_BASE_URL)
    if len(planner_suffix) != 2:
        LOGGER.error(msg := "Invalid planner url")
        raise MaxrollError(msg)
    planner_id, fragment_separator, fragment = planner_suffix[1].partition("#")
    if fragment_separator and fragment.isdecimal():
        data_id = fragment
        data_id = int(data_id) - 1
        build_id_is_visible_position = True
    else:
        try:
            r = get_with_retry(url=PLANNER_API_BASE_URL + planner_id)
        except ConnectionError as exc:
            LOGGER.exception(msg := "Couldn't get planner")
            raise MaxrollError(msg) from exc
        data_id = json.loads(r.json()["data"])["activeProfile"]
        build_id_is_visible_position = False
    return PLANNER_API_BASE_URL + planner_id, data_id, build_id_is_visible_position


def _extract_planner_url_and_id_from_guide(url: str) -> tuple[str, int, bool]:
    """Resolve a build guide to the underlying planner API url and profile selection."""
    try:
        r = get_with_retry(url=url)
    except ConnectionError as exc:
        LOGGER.exception(msg := "Couldn't get build guide")
        raise MaxrollError(msg) from exc
    data = lxml.html.fromstring(r.text)
    # As of season 13, the link to the planner is stuck in a script so we get it from there
    script_elements = data.xpath(SCRIPT_XPATH)
    for script_element in script_elements:
        if script_element.text and script_element.text.strip().startswith(BUILD_SCRIPT_PREFIX):
            planner_match = PLANNER_API_REGEX.search(script_element.text)
            if planner_match is None:
                continue
            planner_link = planner_match.group()
            if planner_link:
                api_url, build_id, build_id_is_visible_position = _extract_planner_url_and_id_from_planner(planner_link)
                return api_url, build_id, build_id_is_visible_position

    msg = "Couldn't resolve a planner profile from this Maxroll build guide. Use the planner link directly and please report a bug."
    LOGGER.error(msg)
    raise MaxrollError(msg)


def _resolve_visible_profile_index(profiles: Sequence[Mapping[str, object]], visible_profile_index: int) -> int:
    visible_index = 0
    for profile_index, profile in enumerate(profiles):
        if profile.get("hidden"):
            continue
        if visible_index == visible_profile_index:
            return profile_index
        visible_index += 1
    return visible_profile_index


__all__ = [name for name in globals() if not name.startswith("__")]
