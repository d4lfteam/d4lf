from __future__ import annotations

import logging
import re

from src.dataloader import Dataloader
from src.item.data.aspect import Aspect
from src.item.data.rarity import ItemRarity
from src.item.descr.text import find_number

LOGGER = logging.getLogger(__name__)

_ASPECT_RE = re.compile(
    r"(?P<affixvalue>[0-9]+[.]?[0-9]*)[^0-9]+\[(?P<minvalue>[0-9]+[.]?[0-9]*)"
    r" - (?P<maxvalue>[0-9]+[.]?[0-9]*)]"
)

_AFFIX_REPLACEMENTS = ["%", "+", ",", "[+]", "[x]", "per 5 Seconds"]
_REPLACE_COMPARE_RE = re.compile(r"\(.*\)")


def get_aspect_text(tts_section: list[str], rarity: ItemRarity, start: int, num_affixes: int) -> str | None:
    if rarity in [ItemRarity.Mythic, ItemRarity.Unique, ItemRarity.Legendary]:
        aspect_index = start + num_affixes
        return tts_section[aspect_index]
    return None


def build_mythic_aspect(text: str, name: str) -> Aspect:
    return Aspect(name=name, text=text, value=find_number(text))


def build_unique_aspect(text: str, name: str) -> Aspect:
    result = Aspect(text=text, name=name)
    for replacement in _AFFIX_REPLACEMENTS:
        text = text.replace(replacement, "")
    text = _REPLACE_COMPARE_RE.sub("", text).strip()

    match = _ASPECT_RE.search(text)
    if match:
        matched_groups = {group_name: value for group_name, value in match.groupdict().items() if value is not None}
        if not matched_groups:
            msg = f"Could not match aspect text: {text}"
            raise Exception(msg)

        if matched_groups.get("minvalue") is not None:
            result.min_value = float(matched_groups["minvalue"])
        if matched_groups.get("maxvalue") is not None:
            result.max_value = float(matched_groups["maxvalue"])
        if matched_groups.get("affixvalue") is not None:
            result.value = float(matched_groups["affixvalue"])

    return result


def build_legendary_aspect(text: str, name: str) -> Aspect | None:
    for aspect_name in Dataloader().aspect_list:
        if aspect_name in name:
            return Aspect(text=text, name=aspect_name)

    LOGGER.warning("Could not find an aspect representing %s in our data.", name)
    return None


def parse_aspect_from_tts_section(tts_section: list[str], item, start: int, num_affixes: int) -> Aspect | None:
    aspect_text = get_aspect_text(tts_section, item.rarity, start, num_affixes)
    if not aspect_text:
        return None

    if item.rarity == ItemRarity.Mythic:
        return build_mythic_aspect(aspect_text, item.name)
    if item.rarity == ItemRarity.Unique:
        return build_unique_aspect(aspect_text, item.name)
    return build_legendary_aspect(aspect_text, item.name)
