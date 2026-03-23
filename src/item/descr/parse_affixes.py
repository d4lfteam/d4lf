from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Callable

import rapidfuzz

from src.dataloader import Dataloader
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType, is_armor, is_jewelry, is_weapon
from src.item.data.rarity import ItemRarity
from src.item.data.seasonal_attribute import SeasonalAttribute
from src.item.descr import keep_letters_and_spaces
from src.item.descr.parse_aspect import parse_aspect_from_tts_section
from src.utils.window import screenshot

if TYPE_CHECKING:
    from src.item.data.aspect import Aspect
    from src.item.models import Item

LOGGER = logging.getLogger(__name__)

_AFFIX_RE = re.compile(
    r"(?P<affixvalue1>[0-9]+)[^0-9]+\[(?P<minvalue1>[0-9]+) - (?P<maxvalue1>[0-9]+)]|"
    r"(?P<affixvalue2>[0-9]+\.[0-9]+).+?\[(?P<minvalue2>[0-9]+\.[0-9]+) - (?P<maxvalue2>[0-9]+\.[0-9]+)]|"
    r"(?P<affixvalue3>[.0-9]+)[^0-9]+\[(?P<onlyvalue>[.0-9]+)]|"
    r".?![^\[\]]*[\[\]](?P<affixvalue4>\d+.?:\.\d+?)(?P<greateraffix1>[ ]*)|"
    r"(?P<greateraffix2>[0-9]+[.0-9]*)(?![^\[]*\[).*",
    re.DOTALL,
)

_REPLACE_COMPARE_RE = re.compile(r"\(.*\)")
_FOR_SECONDS_RE = re.compile(r"for (?P<forsecondsvalue>\d) Seconds")
_AFFIX_REPLACEMENTS = ["%", "+", ",", "[+]", "[x]", "per 5 Seconds"]


def get_item_rarity(data: str) -> ItemRarity | None:
    return next((rar for rar in ItemRarity if rar.value == data.lower()), ItemRarity.Common)


def get_item_type(data: str):
    return next((it for it in ItemType if it.value == data.lower()), None)


def get_affix_starting_location_from_tts_section(tts_section: list[str], item: Item) -> int:
    start = 0

    if is_weapon(item.item_type):
        start = get_index_of_armor_dps_or_all_resist(tts_section, "damage per second") + 2
    elif is_jewelry(item.item_type):
        start = get_index_of_armor_dps_or_all_resist(tts_section, "all resist")
    elif is_armor(item.item_type):
        start = get_index_of_armor_dps_or_all_resist(tts_section, "armor")
    start += 1

    return start


def get_index_of_armor_dps_or_all_resist(tts_section: list[str], indicator: str) -> int:
    for i, line in enumerate(tts_section):
        if indicator == keep_letters_and_spaces(_REPLACE_COMPARE_RE.sub("", line.lower())).strip():
            return i

    return 0


def get_affixes_from_tts_section(tts_section: list[str], start: int, length: int):
    return tts_section[start : start + length]


def get_affix_counts(
    tts_section: list[str], item: Item, start: int, *, dataloader: Dataloader | None = None
) -> tuple[int, int]:
    inherent_num = 0
    affixes_num = 4
    if is_weapon(item.item_type) or item.item_type == ItemType.Boots:
        inherent_num = 1
    elif item.item_type == ItemType.Shield:
        inherent_num = 3

    if item.rarity in [ItemRarity.Unique, ItemRarity.Mythic]:
        if dataloader is None:
            dataloader = Dataloader()
        unique_inherents = dataloader.aspect_unique_dict.get(item.name)["num_inherents"]
        if unique_inherents is not None:
            inherent_num = unique_inherents

    if item.rarity == ItemRarity.Rare and any(
        tts_section[start + inherent_num + affixes_num - 1].lower().startswith(x)
        for x in ["empty socket", "requires level", "properties lost when equipped", "rampage:", "feast:", "hunger:"]
    ):
        affixes_num = 3
    elif item.rarity == ItemRarity.Legendary and tts_section[start + inherent_num + affixes_num - 1].lower().startswith(
        "imprinted:"
    ):
        affixes_num = 3

    if item.seasonal_attribute == SeasonalAttribute.bloodied:
        affixes_num += 1

    return inherent_num, affixes_num


def has_numbers(affix_text: str) -> bool:
    return any(char.isdigit() for char in affix_text)


def get_affix_from_text(text: str, *, dataloader: Dataloader | None = None) -> Affix:
    result = Affix(text=text)
    for replacement in _AFFIX_REPLACEMENTS:
        text = text.replace(replacement, "")
    text = _REPLACE_COMPARE_RE.sub("", text).strip()

    for_seconds_matches = _FOR_SECONDS_RE.findall(text)
    for for_seconds_match in for_seconds_matches:
        for value in [f"for {for_seconds_match} Seconds", f"[{for_seconds_match}]"]:
            text = text.replace(value, "")

    matched_groups: dict[str, str] = {}
    for match in _AFFIX_RE.finditer(text):
        matched_groups = {name: value for name, value in match.groupdict().items() if value is not None}
    if not matched_groups and has_numbers(text):
        msg = f"Could not match affix text: {text}"
        raise Exception(msg)

    for key in ["minvalue1", "minvalue2"]:
        if matched_groups.get(key) is not None:
            result.min_value = float(matched_groups[key])
            break
    for key in ["maxvalue1", "maxvalue2"]:
        if matched_groups.get(key) is not None:
            result.max_value = float(matched_groups[key])
            break
    for key in ["affixvalue1", "affixvalue2", "affixvalue3", "affixvalue4"]:
        if matched_groups.get(key) is not None:
            result.value = float(matched_groups[key])
            break
    for key in ["greateraffix1", "greateraffix2"]:
        if matched_groups.get(key) is not None:
            result.type = AffixType.greater
            if key == "greateraffix2":
                result.value = float(matched_groups[key])
            break
    if matched_groups.get("onlyvalue") is not None:
        result.min_value = float(matched_groups["onlyvalue"])
        result.max_value = float(matched_groups["onlyvalue"])

    if dataloader is None:
        dataloader = Dataloader()
    result.name = rapidfuzz.process.extractOne(
        keep_letters_and_spaces(_REPLACE_COMPARE_RE.sub("", result.text).strip()),
        list(dataloader.affix_dict),
        scorer=rapidfuzz.distance.Levenshtein.distance,
    )[0]
    return result


def _raise_index_error(affixes, affix_bullets, item, img_item_descr):
    LOGGER.error("About to raise index error, dumping information for debug:")
    LOGGER.error(f"Affixes ({len(affixes)}): {affixes}")
    LOGGER.error(f"Affix Bullets ({len(affix_bullets)}): {affix_bullets}")
    LOGGER.error(f"Item: {item}")
    LOGGER.error("Placed screenshot of item in screenshot folder. Screenshot will start with 'not_enough_bullets'")
    screenshot("not_enough_bullets", img=img_item_descr)

    msg = (
        "Found more affixes than we found bullets to represent those affixes. "
        "This could be a temporary issue finding bullet positions on the screen, "
        "but if it happens consistently please open a bug report with a full screen "
        "screenshot with the item hovered on and vision mode disabled. Additionally, "
        "include the ~10 log lines above this message and the screenshot in the screenshot folder."
    )
    raise IndexError(msg)


def add_affixes_from_tts(
    tts_section: list[str],
    item: Item,
    *,
    dataloader: Dataloader | None = None,
    parse_aspect_func: Callable[[list[str], Item, int, int], Aspect | None] = parse_aspect_from_tts_section,
) -> Item:
    starting_index = get_affix_starting_location_from_tts_section(tts_section, item)
    inherent_num, affixes_num = get_affix_counts(tts_section, item, starting_index, dataloader=dataloader)
    affixes = get_affixes_from_tts_section(tts_section, starting_index, inherent_num + affixes_num)
    for i, affix_text in enumerate(affixes):
        if i < inherent_num:
            affix = get_affix_from_text(affix_text, dataloader=dataloader)
            affix.type = AffixType.inherent
            item.inherent.append(affix)
        elif i < inherent_num + affixes_num:
            affix = get_affix_from_text(affix_text, dataloader=dataloader)
            item.affixes.append(affix)

    item.aspect = parse_aspect_func(tts_section, item, starting_index, len(affixes))
    return item


def add_affixes_from_tts_mixed(
    tts_section: list[str],
    item: Item,
    affix_bullets,
    img_item_descr,
    aspect_bullet=None,
    *,
    dataloader: Dataloader | None = None,
    parse_aspect_func: Callable[[list[str], Item, int, int], Aspect | None] = parse_aspect_from_tts_section,
) -> Item:
    starting_index = get_affix_starting_location_from_tts_section(tts_section, item)
    inherent_num, affixes_num = get_affix_counts(tts_section, item, starting_index, dataloader=dataloader)
    affixes = get_affixes_from_tts_section(tts_section, starting_index, inherent_num + affixes_num)

    if len(affixes) - 1 > len(affix_bullets):
        _raise_index_error(affixes, affix_bullets, item, img_item_descr)

    for i, affix_text in enumerate(affixes):
        if i < inherent_num:
            affix = get_affix_from_text(affix_text, dataloader=dataloader)
            affix.type = AffixType.inherent
            affix.loc = affix_bullets[i].center
            item.inherent.append(affix)
        elif i < inherent_num + affixes_num:
            affix = get_affix_from_text(affix_text, dataloader=dataloader)
            affix.loc = affix_bullets[i].center
            if affix_bullets[i].name.startswith("greater_affix"):
                affix.type = AffixType.greater
            elif affix_bullets[i].name.startswith("rerolled"):
                affix.type = AffixType.rerolled
            else:
                affix.type = AffixType.normal
            item.affixes.append(affix)

    item.aspect = parse_aspect_func(tts_section, item, starting_index, len(affixes))
    if item.aspect and aspect_bullet:
        item.aspect.loc = aspect_bullet.center
    return item
