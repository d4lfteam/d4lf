import logging
from typing import TYPE_CHECKING

import rapidfuzz

from src.game_data import GameCatalog, ItemRarity, ItemType, is_armor, is_jewelry, is_weapon
from src.item import Affix, AffixType, Aspect
from src.perception.text import correct_name

if TYPE_CHECKING:
    from src.item import Item

from src.perception.parser.base import _AFFIX_RE, _AFFIX_REPLACEMENTS, _ASPECT_RE, _FOR_SECONDS_RE, _REPLACE_COMPARE_RE
from src.perception.text import keep_letters_and_spaces

LOGGER = logging.getLogger(__name__)


def _update_item_object(item: Item, rarity: ItemRarity | None = None, item_type: ItemType | None = None) -> Item:
    if rarity:
        item.rarity = rarity
    if item_type:
        item.item_type = item_type

    return item


def _get_affix_starting_location_from_tts_section(tts_section: list[str], item: Item) -> int:
    start = 0

    if is_weapon(item.item_type):
        start = _get_index_of_armor_dps_or_all_resist(tts_section, "damage per second") + 2
    elif is_jewelry(item.item_type):
        start = _get_index_of_armor_dps_or_all_resist(tts_section, "all resist")
    elif item.item_type == ItemType.Shield:
        start = _get_index_of_armor_dps_or_all_resist(tts_section, "armor") + 2
    elif is_armor(item.item_type):
        start = _get_index_of_armor_dps_or_all_resist(tts_section, "armor")
    elif item.item_type == ItemType.HoradricSeal:
        index = _get_index_after_item_power(tts_section, fallback=4)
        return _skip_armory_loadout_banner(tts_section, index)
    elif item.item_type == ItemType.Charm:
        index = _get_index_after_item_power(tts_section, fallback=3)
        return _skip_armory_loadout_banner(tts_section, index)
    start += 1

    return start


def _skip_armory_loadout_banner(tts_section: list[str], index: int) -> int:
    """Equipped seals/charms may show an "Armory Loadout" banner right after Item Power; skip past it."""
    if index < len(tts_section) and "armory loadout" in tts_section[index].lower():
        return index + 1
    return index


def _get_index_of_armor_dps_or_all_resist(tts_section: list[str], indicator: str) -> int:
    for i, line in enumerate(tts_section):
        if indicator == keep_letters_and_spaces(_REPLACE_COMPARE_RE.sub("", line.lower())).strip():
            return i

    return 0


def _get_index_after_item_power(tts_section: list[str], fallback: int) -> int:
    """Get index after item power.

    Seals/charms have no unique anchor text near their affixes (unlike "armor"/"all resist"/"damage per
    second" for other item types), so we anchor on the "Item Power" line instead. This stays correct even
    when Diablo inserts extra lines above it, e.g. an Armory loadout banner on equipped charms/seals.
    """
    for i, line in enumerate(tts_section):
        if "item power" in line.lower():
            return i + 1

    LOGGER.warning(f"Could not find 'Item Power' line in TTS section, falling back to index {fallback}: {tts_section}")
    return fallback


def _get_affixes_from_tts_section(tts_section: list[str], start: int, length: int) -> list[str]:
    return tts_section[start : start + length]


def _get_aspect_or_set_from_tts_section(tts_section: list[str], item: Item, start: int, num_affixes: int) -> str | None:
    if item.item_type == ItemType.HoradricSeal and item.rarity == ItemRarity.Legendary:
        return None
    # Grab the aspect/set as well in this case
    if item.rarity in [ItemRarity.Mythic, ItemRarity.Unique, ItemRarity.Legendary]:
        aspect_index = start + num_affixes
        return tts_section[aspect_index]
    if item.rarity == ItemRarity.Set:
        for line in tts_section[start + num_affixes :]:
            set_name = _get_set_from_text(line)
            if set_name:
                return set_name

    return None


def _get_set_from_text(set_text: str) -> str | None:
    set_name = correct_name(set_text)
    if set_name in GameCatalog().bad_tts_uniques:
        set_name = GameCatalog().bad_tts_uniques[set_name]
    if set_name in GameCatalog().set_list:
        return set_name
    return None


def _get_affix_from_text(text: str, item_type: ItemType | None = None) -> Affix:
    result = Affix(text=text)

    text = _clean_value_text(text)

    # A semi-hacky way to handle "for X Seconds", which will get read as a GA if we do nothing
    for_seconds_matches = _FOR_SECONDS_RE.findall(text)
    for for_seconds_match in for_seconds_matches:
        for x in [f"for {for_seconds_match} Seconds", f"[{for_seconds_match}]"]:
            text = text.replace(x, "")

    matched_groups: dict[str, str] = {}
    for match in _AFFIX_RE.finditer(text):
        matched_groups = {name: value for name, value in match.groupdict().items() if isinstance(value, str)}
    if not matched_groups and _has_numbers(text):
        msg = f"Could not match affix text: {text}"
        raise Exception(msg)
    for x in ["minvalue1", "minvalue2"]:
        if (value := matched_groups.get(x)) is not None:
            result.min_value = float(value)
            break
    for x in ["maxvalue1", "maxvalue2"]:
        if (value := matched_groups.get(x)) is not None:
            result.max_value = float(value)
            break
    for x in ["affixvalue1", "affixvalue2", "affixvalue3", "affixvalue4"]:
        if (value := matched_groups.get(x)) is not None:
            result.value = float(value)
            break
    for x in ["greateraffix1", "greateraffix2"]:
        if matched_groups.get(x) is not None:
            result.type = AffixType.greater
            if x == "greateraffix2":
                result.value = float(matched_groups[x])
            break
    if (only_value := matched_groups.get("onlyvalue")) is not None:
        result.min_value = float(only_value)
        result.max_value = float(only_value)

    if "Charm Slot" in text:  # These are never greater even if they look like they are greater
        result.type = AffixType.normal

    affix_dict = _get_affix_dictionary(item_type)
    match = rapidfuzz.process.extractOne(
        keep_letters_and_spaces(_REPLACE_COMPARE_RE.sub("", result.text).strip()),
        list(affix_dict),
        scorer=rapidfuzz.distance.Levenshtein.distance,
    )
    if match is None or not isinstance(match[0], str):
        msg = f"Could not match affix name: {result.text}"
        raise ValueError(msg)
    result.name = match[0]
    return result


def _has_numbers(affix_text: str) -> bool:
    return any(char.isdigit() for char in affix_text)


def _clean_value_text(text: str) -> str:
    """Strip the noise tokens (%, +, commas, comparison parentheses, etc.) that surround a numeric value."""
    for x in _AFFIX_REPLACEMENTS:
        text = text.replace(x, "")
    return _REPLACE_COMPARE_RE.sub("", text).strip()


def _get_affix_dictionary(item_type: ItemType | None) -> dict[str, str]:
    if item_type == ItemType.HoradricSeal:
        return GameCatalog().affix_dict | GameCatalog().seal_affix_dict
    if item_type == ItemType.Charm:
        return GameCatalog().affix_dict | GameCatalog().charm_affix_dict
    return GameCatalog().affix_dict


def _is_known_affix_text(text: str, item_type: ItemType | None) -> bool:
    normalized_text = keep_letters_and_spaces(_REPLACE_COMPARE_RE.sub("", text).strip()).casefold()
    return any(
        normalized_text == keep_letters_and_spaces(affix_text).casefold()
        for affix_text in _get_affix_dictionary(item_type).values()
    )


# For unique aspects
def _get_aspect_from_text(text: str, name: str) -> Aspect:
    result = Aspect(text=text, name=name)
    text = _clean_value_text(text)

    match = _ASPECT_RE.search(text)
    if match:  # No match means the aspect is text only, there are no values to filter on
        matched_groups = {name: value for name, value in match.groupdict().items() if value is not None}
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


# For legendary aspects
def _get_aspect_from_name(text: str, name: str) -> Aspect | None:
    for aspect_name in GameCatalog().aspect_list:
        if aspect_name in name:
            return Aspect(text=text, name=aspect_name)

    LOGGER.warning(f"Could not find an aspect representing {name} in our data.")
    return None


def _get_item_rarity(data: str) -> ItemRarity | None:
    return next((rar for rar in ItemRarity if rar.value == data.lower()), ItemRarity.Common)


def _get_item_type(data: str) -> ItemType | None:
    return GameCatalog().item_type_from_text(data)


def _item_type_text_matches(data: str, item_type: ItemType) -> bool:
    normalized = data.strip().casefold()
    return any(normalized == candidate.strip().casefold() for candidate in GameCatalog().item_type_names(item_type))


def _has_item_type_suffix(data: str, item_type: ItemType) -> bool:
    normalized = data.strip().casefold()
    return any(
        normalized.endswith(candidate.strip().casefold()) for candidate in GameCatalog().item_type_names(item_type)
    )


def _has_item_type_prefix(data: str, item_type: ItemType) -> bool:
    normalized = data.strip().casefold()
    return any(
        normalized.startswith(candidate.strip().casefold()) for candidate in GameCatalog().item_type_names(item_type)
    )


def _is_codex_upgrade(tts_section: list[str]) -> bool:
    return any(
        "upgrades an aspect in the codex of power" in line.lower() or "unlocks new aspect" in line.lower()
        for line in tts_section
    )


def _is_cosmetic_upgrade(tts_section: list[str]) -> bool:
    return any("unlocks new look on salvage" in line.lower() for line in tts_section)
