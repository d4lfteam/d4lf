import copy
import logging
import re

import rapidfuzz

import src.tts
from src.dataloader import Dataloader
from src.item.data.affix import Affix, AffixType
from src.item.data.aspect import Aspect
from src.item.data.item_type import (
    ItemType,
    is_armor,
    is_consumable,
    is_jewelry,
    is_non_sigil_mapping,
    is_seal_or_charm,
    is_sigil,
    is_socketable,
    is_weapon,
)
from src.item.data.rarity import ItemRarity
from src.item.data.seasonal_attribute import SeasonalAttribute
from src.item.descr import keep_letters_and_spaces
from src.item.descr.text import find_number
from src.item.models import Item
from src.item.sigil_rules import SigilRules
from src.scripts import correct_name
from src.tts import ItemIdentifiers

_AFFIX_RE = re.compile(
    r"(?P<affixvalue1>[0-9]+)[^0-9]+\[(?P<minvalue1>[0-9]+) - (?P<maxvalue1>[0-9]+)]|"
    r"(?P<affixvalue2>[0-9]+\.[0-9]+).+?\[(?P<minvalue2>[0-9]+\.[0-9]+) - (?P<maxvalue2>[0-9]+\.[0-9]+)]|"
    r"(?P<affixvalue3>[.0-9]+)[^0-9]+\[(?P<onlyvalue>[.0-9]+)]|"
    r".?![^\[\]]*[\[\]](?P<affixvalue4>\d+.?:\.\d+?)(?P<greateraffix1>[ ]*)|"
    r"(?P<greateraffix2>[0-9]+[.0-9]*)(?![^\[]*\[).*",
    re.DOTALL,
)

_ASPECT_RE = re.compile(
    r"(?P<affixvalue>[0-9]+[.]?[0-9]*)[^0-9]+\[(?P<minvalue>[0-9]+[.]?[0-9]*)"
    r" - (?P<maxvalue>[0-9]+[.]?[0-9]*)]"
)

_FOR_SECONDS_RE = re.compile(r"for (?P<forsecondsvalue>\d+(?:\.\d+)?) Seconds")

_REPLACE_COMPARE_RE = re.compile(r"\(.*\)")

_AFFIX_REPLACEMENTS = ["%", "+", ",", "[+]", "[x]", "per 5 Seconds"]
_AFFIX_STOP_MARKERS = (
    "empty socket",
    "requires level",
    "properties lost when equipped",
    "cannot salvage",
    "sell value",
    "rampage:",
    "feast:",
    "hunger:",
    "right mouse button",
    "left mouse button",
    "action button",
)
LOGGER = logging.getLogger(__name__)


# Returns a tuple with the number of affixes.  It's in the format (inherent_num, affixes_num)
def _get_affix_counts(tts_section: list[str], item: Item, start: int) -> tuple[int, int]:
    inherent_num = 0
    affixes_num = 4
    # We assume these objects have the minimum number of affixes and then try to determine if they have more.
    if item.rarity == ItemRarity.Common:
        affixes_num = 0
    elif item.rarity == ItemRarity.Magic:
        affixes_num = 1
    elif item.rarity == ItemRarity.Rare:
        affixes_num = 2 if is_seal_or_charm(item.item_type) else 3
    elif item.rarity == ItemRarity.Legendary:
        affixes_num = 3 if is_seal_or_charm(item.item_type) else 4
    elif item.rarity == ItemRarity.Set:
        affixes_num = 2
    elif item.rarity == ItemRarity.Unique:
        affixes_num = 2 if is_seal_or_charm(item.item_type) else 4

    if item.rarity in [ItemRarity.Unique, ItemRarity.Mythic] and item.name is not None:
        # Uniques can have variable amounts of inherents.
        unique_data = Dataloader().aspect_unique_dict.get(item.name)
        if unique_data is not None and unique_data["num_inherents"] is not None:
            inherent_num = unique_data["num_inherents"]

    # Rares have either 3 or 4 affixes so we have to do special handling to figure out where exactly the affixes end.
    # This will also grab up slotted gems but we really don't have much choice
    next_line_index = start + inherent_num + affixes_num
    if (
        item.rarity in [ItemRarity.Magic, ItemRarity.Rare]
        and next_line_index < len(tts_section)
        and not any(tts_section[next_line_index].lower().startswith(x) for x in _AFFIX_STOP_MARKERS)
    ):
        affixes_num = affixes_num + 1
    elif item.rarity == ItemRarity.Legendary and tts_section[start + inherent_num + affixes_num - 1].lower().startswith(
        "imprinted:"
    ):
        # Additionally, if someone imprinted a 3 affix rare we'd think it was a legendary so we need to catch those here
        affixes_num = 3
    elif item.rarity in [ItemRarity.Legendary, ItemRarity.Unique, ItemRarity.Mythic]:
        while (
            next_line_index < len(tts_section)
            and _is_known_affix_text(tts_section[next_line_index], item.item_type)
            and not any(tts_section[next_line_index].lower().startswith(x) for x in _AFFIX_STOP_MARKERS)
        ):
            affixes_num += 1
            next_line_index += 1

    if item.seasonal_attribute == SeasonalAttribute.bloodied:
        affixes_num = affixes_num + 1

    return inherent_num, affixes_num


def _compute_affix_layout(tts_section: list[str], item: Item) -> tuple[int, int, list[str], str | None]:
    """Compute where affixes start/end and what (if any) aspect/set text follows them.

    Returns (inherent_num, affixes_num, affixes, aspect_or_set_text).
    """
    starting_index = _get_affix_starting_location_from_tts_section(tts_section, item)
    inherent_num, affixes_num = _get_affix_counts(tts_section, item, starting_index)
    affixes = _get_affixes_from_tts_section(tts_section, starting_index, inherent_num + affixes_num)
    aspect_or_set_text = _get_aspect_or_set_from_tts_section(tts_section, item, starting_index, len(affixes))
    return inherent_num, affixes_num, affixes, aspect_or_set_text


def _assign_aspect_or_set(item: Item, aspect_or_set_text: str | None) -> None:
    if not aspect_or_set_text or item.name is None:
        return
    if item.rarity == ItemRarity.Mythic:
        item.aspect = Aspect(name=item.name, text=aspect_or_set_text, value=find_number(aspect_or_set_text))
    elif item.rarity == ItemRarity.Unique:
        item.aspect = _get_aspect_from_text(aspect_or_set_text, item.name)
    elif item.rarity == ItemRarity.Set:
        item.set = aspect_or_set_text
    else:
        item.aspect = _get_aspect_from_name(aspect_or_set_text, item.name)


def _add_affixes_from_tts(tts_section: list[str], item: Item) -> Item:
    inherent_num, affixes_num, affixes, aspect_or_set_text = _compute_affix_layout(tts_section, item)
    for i, affix_text in enumerate(affixes):
        if i < inherent_num:
            affix = _get_affix_from_text(affix_text, item.item_type)
            affix.type = AffixType.inherent
            item.inherent.append(affix)
        elif i < inherent_num + affixes_num:
            affix = _get_affix_from_text(affix_text, item.item_type)
            item.affixes.append(affix)

    _assign_aspect_or_set(item, aspect_or_set_text)
    return item


def _add_sigil_affixes_from_tts(tts_section: list[str], item: Item) -> Item:
    name_index = (
        3 if item.item_type == ItemType.EscalationSigil or item.seasonal_attribute == SeasonalAttribute.bloodied else 2
    )
    name = tts_section[name_index].split(" in ")[0]
    item.name = correct_name(name)

    start = next((i for i, s in enumerate(tts_section) if "AFFIXES" in s), None)
    if start:
        first_affix_index = start + 1
        second_affix_index = start + 3
    else:
        msg = f"Could not find string AFFIXES in TTS provided by Diablo. Sigil filtering may be unstable, please open a bug with this info: {tts_section}"
        LOGGER.error(msg)
        first_affix_index = 4
        second_affix_index = 6

    affixes = [tts_section[first_affix_index], tts_section[second_affix_index]]

    for affix_name in affixes:
        normalized_name = correct_name(keep_letters_and_spaces(affix_name))
        if normalized_name is None:
            normalized_name = ""
        affix = Affix(name=normalized_name)
        affix.type = AffixType.normal
        item.affixes.append(affix)

    item.rarity = SigilRules.default().for_item(item).rarity

    return item


def _create_base_item_from_tts(tts_item: list[str]) -> Item | None:
    item = Item(original_name=tts_item[0])
    if tts_item[1].endswith(ItemIdentifiers.COMPASS.value):
        return _update_item_object(item, rarity=ItemRarity.Common, item_type=ItemType.Compass)
    if ItemIdentifiers.NIGHTMARE_SIGIL.value.upper() in tts_item[0].upper():
        if "Nightmare Sigil is used" in tts_item[0]:  # This is actually the crafting screen
            return None
        if "bloodied" in tts_item[1].lower():
            item.seasonal_attribute = SeasonalAttribute.bloodied
        return _update_item_object(item, item_type=ItemType.Sigil)
    if tts_item[0].startswith(ItemIdentifiers.ESCALATION_SIGIL.value):
        return _update_item_object(item, item_type=ItemType.EscalationSigil)
    if ItemIdentifiers.TRIBUTE.value in tts_item[0]:
        item.item_type = ItemType.Tribute
        search_string_split = tts_item[1].split(" ")
        item.rarity = _get_item_rarity(search_string_split[0])
        item.name = correct_name(" ".join(search_string_split[1:]))
        return item
    if tts_item[0].startswith(ItemIdentifiers.WHISPERING_KEY.value):
        return _update_item_object(item, item_type=ItemType.Consumable)
    if any(tts_item[1].lower().endswith(x) for x in ["summoning"]):
        return _update_item_object(item, item_type=ItemType.Material)
    if any(tts_item[1].lower().endswith(x) for x in ["gem"]):
        return _update_item_object(item, item_type=ItemType.Gem)
    if any(tts_item[1].lower().endswith(x) for x in ["whispering wood"]):
        return _update_item_object(item, item_type=ItemType.WhisperingWood)
    if any(tts_item[1].lower().startswith(x) for x in ["cosmetic"]):
        return _update_item_object(item, item_type=ItemType.Cosmetic)
    if any(tts_item[1].lower().endswith(x) for x in ["boss key"]):
        return _update_item_object(item, item_type=ItemType.LairBossKey)
    if "rune of" in tts_item[1].lower():
        item.item_type = ItemType.Rune
        search_string_split = tts_item[1].lower().split(" rune of ")
        item.rarity = _get_item_rarity(search_string_split[0])
        return item
    if any("Cost : " in value or "Cost:" in value for value in tts_item):
        item.is_in_shop = True
    if any(tts_item[1].lower().endswith(x) for x in ["cache"]):
        item.item_type = ItemType.Cache
        return item
    if tts_item[1].lower().endswith("elixir"):
        item.item_type = ItemType.Elixir
    elif tts_item[1].lower().endswith("incense"):
        item.item_type = ItemType.Incense
    elif "temper manual" in tts_item[1].lower():
        item.item_type = ItemType.TemperManual
    elif any(tts_item[1].lower().endswith(x) for x in ["consumable", "scroll"]):
        item.item_type = ItemType.Consumable
    if is_consumable(item.item_type):
        search_string_split = tts_item[1].split(" ")
        item.rarity = _get_item_rarity(search_string_split[0])
        return item
    if "bloodied" in tts_item[1].lower():
        item.seasonal_attribute = SeasonalAttribute.bloodied
    item.is_ancestral = "ancestral" in tts_item[1].lower()

    # Check lines 3-6 instead of just line 4 (handles variable name lengths and gives us flexibility to search for the sanctified marker)
    if any("sanctified" in tts_item[i].lower() for i in range(3, min(7, len(tts_item)))):
        item.seasonal_attribute = SeasonalAttribute.sanctified

    search_string = tts_item[1].lower().replace("ancestral", "").replace("bloodied", "").strip()
    search_string = _REPLACE_COMPARE_RE.sub("", search_string).strip()
    search_string_split = search_string.split(" ")
    item.rarity = _get_item_rarity(search_string_split[0])
    starting_item_type_index = 1
    if item.rarity == ItemRarity.Mythic:
        starting_item_type_index = 2
    elif item.rarity == ItemRarity.Common:
        starting_item_type_index = 0
    item.item_type = _get_item_type(" ".join(search_string_split[starting_item_type_index:]))
    item.name = correct_name(tts_item[0])
    if item.name in Dataloader().bad_tts_uniques:
        item.name = Dataloader().bad_tts_uniques[item.name]
    for line in tts_item:
        if "item power" in line.lower():
            item_power = find_number(line)
            if item_power is None:
                return None
            item.power = int(item_power)
            break
    return item


def _update_item_object(item: Item, rarity=None, item_type=None) -> Item:
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
        index = _skip_armory_loadout_banner(tts_section, index)
        # Seals also report their max charm slot count right after Item Power; skip past it to reach the affixes.
        if index < len(tts_section) and "charm slot" in tts_section[index].lower():
            index += 1
        return index
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


def _get_affixes_from_tts_section(tts_section: list[str], start: int, length: int):
    return tts_section[start : start + length]


def _get_aspect_or_set_from_tts_section(tts_section: list[str], item: Item, start: int, num_affixes: int):
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
    if set_name in Dataloader().bad_tts_uniques:
        set_name = Dataloader().bad_tts_uniques[set_name]
    if set_name in Dataloader().set_list:
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


def _has_numbers(affix_text):
    return any(char.isdigit() for char in affix_text)


def _clean_value_text(text: str) -> str:
    """Strip the noise tokens (%, +, commas, comparison parentheses, etc.) that surround a numeric value."""
    for x in _AFFIX_REPLACEMENTS:
        text = text.replace(x, "")
    return _REPLACE_COMPARE_RE.sub("", text).strip()


def _get_affix_dictionary(item_type: ItemType | None) -> dict[str, str]:
    if item_type == ItemType.HoradricSeal:
        return Dataloader().affix_dict | Dataloader().seal_affix_dict
    if item_type == ItemType.Charm:
        return Dataloader().affix_dict | Dataloader().charm_affix_dict
    return Dataloader().affix_dict


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
    for aspect_name in Dataloader().aspect_list:
        if aspect_name in name:
            return Aspect(text=text, name=aspect_name)

    LOGGER.warning(f"Could not find an aspect representing {name} in our data.")
    return None


def _get_item_rarity(data: str) -> ItemRarity | None:
    return next((rar for rar in ItemRarity if rar.value == data.lower()), ItemRarity.Common)


def _get_item_type(data: str):
    return next((it for it in ItemType if it.value == data.lower()), None)


def _is_codex_upgrade(tts_section: list[str]) -> bool:
    return any(
        "upgrades an aspect in the codex of power" in line.lower() or "unlocks new aspect" in line.lower()
        for line in tts_section
    )


def _is_cosmetic_upgrade(tts_section: list[str]):
    return any("unlocks new look on salvage" in line.lower() for line in tts_section)


class _TtsItemParser:
    def __init__(self, tts_section: list[str]):
        self.tts_section = tts_section
        self.item: Item | None = None

    def parse(self) -> Item | None:
        if not self.tts_section:
            return None
        if (item := _create_base_item_from_tts(self.tts_section)) is None:
            return None
        self.item = item

        if is_sigil(item.item_type):
            return _add_sigil_affixes_from_tts(self.tts_section, item)
        if item.item_type == ItemType.Cosmetic:
            item.cosmetic_upgrade = True
            return item
        if self._should_return_without_affixes():
            return item
        if not self._is_supported_equipment():
            return None
        if item.rarity == ItemRarity.Mythic and item.is_in_shop:
            return None

        self._validate_unique()
        self._add_upgrade_flags()
        return _add_affixes_from_tts(self.tts_section, item)

    @property
    def _current_item(self) -> Item:
        if self.item is None:
            msg = "TTS parser item has not been initialized"
            raise RuntimeError(msg)
        return self.item

    def _should_return_without_affixes(self) -> bool:
        item = self._current_item
        terminal_item_types = [ItemType.Material, ItemType.Tribute, ItemType.Cache, ItemType.LairBossKey]
        if item.seasonal_attribute == SeasonalAttribute.sanctified:
            return True
        return any([
            is_consumable(item.item_type),
            is_non_sigil_mapping(item.item_type),
            is_socketable(item.item_type),
            item.item_type in terminal_item_types,
        ])

    def _is_supported_equipment(self) -> bool:
        item = self._current_item
        return any([
            is_armor(item.item_type),
            is_jewelry(item.item_type),
            is_weapon(item.item_type),
            is_seal_or_charm(item.item_type),
        ])

    def _validate_unique(self) -> None:
        item = self._current_item
        if item.rarity == ItemRarity.Unique and item.name not in Dataloader().aspect_unique_dict:
            msg = (
                f"Unrecognized unique {item.name}. This most likely means the name of it reported "
                f"from Diablo 4 is wrong. Please report a bug with this message."
                f" TTS: {self.tts_section}"
            )
            raise IndexError(msg)
        if item.rarity == ItemRarity.Mythic and item.name not in Dataloader().aspect_unique_dict:
            msg = f"Unrecognized unique {item.name}. This most likely means the name of it reported from Diablo 4 is wrong. Please report a bug with this message. TTS: {self.tts_section}"
            raise IndexError(msg)

    def _add_upgrade_flags(self) -> None:
        item = self._current_item
        item.codex_upgrade = _is_codex_upgrade(self.tts_section)
        item.cosmetic_upgrade = _is_cosmetic_upgrade(self.tts_section)


def read_descr() -> Item | None:
    tts_section = copy.copy(src.tts.LAST_ITEM)
    return _TtsItemParser(tts_section).parse()
