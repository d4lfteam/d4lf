import copy
import logging
import re
from typing import TYPE_CHECKING

import rapidfuzz

import src.tts
from src import TP
from src.dataloader import Dataloader
from src.item.data.affix import Affix, AffixType
from src.item.data.aspect import Aspect
from src.item.data.item_type import (
    ItemType,
    is_armor,
    is_consumable,
    is_jewelry,
    is_non_sigil_mapping,
    is_sigil,
    is_socketable,
    is_weapon,
)
from src.item.data.rarity import ItemRarity
from src.item.descr import keep_letters_and_spaces
from src.item.descr.text import find_number
from src.item.descr.texture import find_affix_bullets, find_aspect_bullet, find_seperator_short, find_seperators_long
from src.item.models import Item
from src.scripts import correct_name
from src.utils.window import screenshot

if TYPE_CHECKING:
    import numpy as np

    from src.template_finder import TemplateMatch

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

_FOR_SECONDS_RE = re.compile(r"for (?P<forsecondsvalue>\d) Seconds")

_REPLACE_COMPARE_RE = re.compile(r"\(.*\)")

_AFFIX_REPLACEMENTS = ["%", "+", ",", "[+]", "[x]", "per 5 Seconds"]
LOGGER = logging.getLogger(__name__)


# Returns a tuple with the number of affixes.  It's in the format (inherent_num, affixes_num)
def _get_affix_counts(tts_section: list[str], item: Item, start: int) -> tuple[int, int]:
    inherent_num = 0
    affixes_num = 4
    if is_weapon(item.item_type) or item.item_type == ItemType.Boots:
        inherent_num = 1
    elif item.item_type == ItemType.Shield:
        inherent_num = 3

    if item.rarity in [ItemRarity.Unique, ItemRarity.Mythic]:
        # Uniques can have variable amounts of inherents.
        unique_inherents = Dataloader().aspect_unique_dict.get(item.name)["num_inherents"]
        if unique_inherents is not None:
            inherent_num = unique_inherents

    # Rares have either 3 or 4 affixes so we have to do special handling to figure out where exactly the affixes end.
    # This will also grab up slotted gems but we really don't have much choice
    if item.rarity == ItemRarity.Rare and any(
        tts_section[start + inherent_num + affixes_num - 1].lower().startswith(x)
        for x in ["empty socket", "requires level", "properties lost when equipped"]
    ):
        affixes_num = 3
    elif item.rarity == ItemRarity.Legendary and tts_section[start + inherent_num + affixes_num - 1].lower().startswith(
        "imprinted:"
    ):
        # Additionally, if someone imprinted a 3 affix rare we'd think it was a legendary so we need to catch those here
        affixes_num = 3

    return inherent_num, affixes_num


def _add_affixes_from_tts(tts_section: list[str], item: Item) -> Item:
    starting_index = _get_affix_starting_location_from_tts_section(tts_section, item)
    inherent_num, affixes_num = _get_affix_counts(tts_section, item, starting_index)
    affixes = _get_affixes_from_tts_section(tts_section, item, starting_index, inherent_num + affixes_num)
    for i, affix_text in enumerate(affixes):
        if i < inherent_num:
            affix = _get_affix_from_text(affix_text)
            affix.type = AffixType.inherent
            item.inherent.append(affix)
        elif i < inherent_num + affixes_num:
            affix = _get_affix_from_text(affix_text)
            item.affixes.append(affix)
        elif item.rarity == ItemRarity.Mythic:
            item.aspect = Aspect(name=item.name, text=affix_text, value=find_number(affix_text))
        elif item.rarity == ItemRarity.Unique:
            item.aspect = _get_aspect_from_text(affix_text, item.name)
        else:
            item.aspect = _get_aspect_from_name(affix_text, item.name)
    return item


def _add_affixes_from_tts_mixed(
    tts_section: list[str],
    item: Item,
    affix_bullets: list[TemplateMatch],
    img_item_descr: np.ndarray,
    aspect_bullet: TemplateMatch | None,
) -> Item:
    starting_index = _get_affix_starting_location_from_tts_section(tts_section, item)
    inherent_num, affixes_num = _get_affix_counts(tts_section, item, starting_index)
    affixes = _get_affixes_from_tts_section(tts_section, item, starting_index, inherent_num + affixes_num)

    # With advanced item compare on we'll actually find more bullets than we need, so we don't rely on them for number of affixes
    if len(affixes) - 1 > len(affix_bullets):
        _raise_index_error(affixes, affix_bullets, item, img_item_descr)

    for i, affix_text in enumerate(affixes):
        if i < inherent_num:
            affix = _get_affix_from_text(affix_text)
            affix.type = AffixType.inherent
            affix.loc = affix_bullets[i].center
            item.inherent.append(affix)
        elif i < inherent_num + affixes_num:
            affix = _get_affix_from_text(affix_text)
            affix.loc = affix_bullets[i].center
            if affix_bullets[i].name.startswith("greater_affix"):
                affix.type = AffixType.greater
            elif affix_bullets[i].name.startswith("rerolled"):
                affix.type = AffixType.rerolled
            else:
                affix.type = AffixType.normal
            item.affixes.append(affix)
        else:
            if item.rarity == ItemRarity.Mythic:
                item.aspect = Aspect(name=item.name, text=affix_text, value=find_number(affix_text))
            elif item.rarity == ItemRarity.Unique:
                item.aspect = _get_aspect_from_text(affix_text, item.name)
            else:
                item.aspect = _get_aspect_from_name(affix_text, item.name)
            if item.aspect:
                if not aspect_bullet:
                    LOGGER.warning(
                        "No bullet was found for the aspect. If the aspect's first line is partially or fully off "
                        "the screen, you can ignore this warning. Otherwise, please report a bug with a screenshot "
                        "of the item."
                    )
                else:
                    item.aspect.loc = aspect_bullet.center
    return item


def _raise_index_error(affixes, affix_bullets, item, img_item_descr: np.ndarray):
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


def _add_sigil_affixes_from_tts(tts_section: list[str], item: Item) -> Item:
    name_index = 3 if item.item_type == ItemType.EscalationSigil else 2
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
        affix = Affix(name=correct_name(keep_letters_and_spaces(affix_name)))
        affix.type = AffixType.normal
        item.affixes.append(affix)

    return item


def _create_base_item_from_tts(tts_item: list[str]) -> Item | None:
    if tts_item[1].endswith(src.tts.ItemIdentifiers.COMPASS.value):
        return Item(rarity=ItemRarity.Common, item_type=ItemType.Compass)
    if tts_item[0].startswith(src.tts.ItemIdentifiers.NIGHTMARE_SIGIL.value):
        if "Nightmare Sigil is used" in tts_item[0]:  # This is actually the crafting screen
            return None
        return Item(rarity=ItemRarity.Common, item_type=ItemType.Sigil)
    if tts_item[0].startswith(src.tts.ItemIdentifiers.ESCALATION_SIGIL.value):
        return Item(rarity=ItemRarity.Common, item_type=ItemType.EscalationSigil)
    if src.tts.ItemIdentifiers.TRIBUTE.value in tts_item[0]:
        item = Item(item_type=ItemType.Tribute)
        search_string_split = tts_item[1].split(" ")
        item.rarity = _get_item_rarity(search_string_split[0])
        item.name = correct_name(" ".join(search_string_split[1:]))
        return item
    if tts_item[0].startswith(src.tts.ItemIdentifiers.WHISPERING_KEY.value):
        return Item(item_type=ItemType.Consumable)
    if any(tts_item[1].lower().endswith(x) for x in ["summoning"]):
        return Item(item_type=ItemType.Material)
    if any(tts_item[1].lower().endswith(x) for x in ["gem"]):
        return Item(item_type=ItemType.Gem)
    if any(tts_item[1].lower().endswith(x) for x in ["whispering wood"]):
        return Item(item_type=ItemType.WhisperingWood)
    if any(tts_item[1].lower().startswith(x) for x in ["cosmetic"]):
        return Item(item_type=ItemType.Cosmetic)
    if any(tts_item[1].lower().endswith(x) for x in ["boss key"]):
        return Item(item_type=ItemType.LairBossKey)
    if "rune of" in tts_item[1].lower():
        item = Item(item_type=ItemType.Rune)
        search_string_split = tts_item[1].lower().split(" rune of ")
        item.rarity = _get_item_rarity(search_string_split[0])
        return item
    item = Item()
    if any("Cost : " in value for value in tts_item):
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

    if "chaos" in tts_item[1].lower():
        item.is_chaos = True

    if (len(tts_item) > 3 and "sanctified" in tts_item[3].lower()) or (
        len(tts_item) > 4 and "sanctified" in tts_item[4].lower()
    ):
        item.sanctified = True

    search_string = tts_item[1].lower().replace("ancestral", "").replace("chaos", "").strip()
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
            item.power = int(find_number(line))
            break
    return item


def _get_affix_starting_location_from_tts_section(tts_section: list[str], item: Item) -> int:
    start = 0

    if is_weapon(item.item_type):
        start = _get_index_of_armor_dps_or_all_resist(tts_section, "damage per second") + 2
    elif is_jewelry(item.item_type):
        start = _get_index_of_armor_dps_or_all_resist(tts_section, "all resist")
    elif is_armor(item.item_type):
        start = _get_index_of_armor_dps_or_all_resist(tts_section, "armor")
    start += 1

    return start


def _get_index_of_armor_dps_or_all_resist(tts_section: list[str], indicator: str) -> int:
    for i, line in enumerate(tts_section):
        if indicator == keep_letters_and_spaces(_REPLACE_COMPARE_RE.sub("", line.lower())).strip():
            return i

    return 0


def _get_affixes_from_tts_section(tts_section: list[str], item: Item, start: int, length: int):
    # Grab the aspect as well in this case
    if item.rarity in [ItemRarity.Mythic, ItemRarity.Unique, ItemRarity.Legendary]:
        length += 1

    return tts_section[start : start + length]


def _get_affix_from_text(text: str) -> Affix:
    result = Affix(text=text)
    for x in _AFFIX_REPLACEMENTS:
        text = text.replace(x, "")
    text = _REPLACE_COMPARE_RE.sub("", text).strip()

    # A semi-hacky way to handle "for X Seconds", which will get read as a GA if we do nothing
    for_seconds_matches = _FOR_SECONDS_RE.findall(text)
    for for_seconds_match in for_seconds_matches:
        for x in [f"for {for_seconds_match} Seconds", f"[{for_seconds_match}]"]:
            text = text.replace(x, "")

    matched_groups = {}
    for match in _AFFIX_RE.finditer(text):
        matched_groups = {name: value for name, value in match.groupdict().items() if value is not None}
    if not matched_groups and _has_numbers(text):
        msg = f"Could not match affix text: {text}"
        raise Exception(msg)
    for x in ["minvalue1", "minvalue2"]:
        if matched_groups.get(x) is not None:
            result.min_value = float(matched_groups[x])
            break
    for x in ["maxvalue1", "maxvalue2"]:
        if matched_groups.get(x) is not None:
            result.max_value = float(matched_groups[x])
            break
    for x in ["affixvalue1", "affixvalue2", "affixvalue3", "affixvalue4"]:
        if matched_groups.get(x) is not None:
            result.value = float(matched_groups[x])
            break
    for x in ["greateraffix1", "greateraffix2"]:
        if matched_groups.get(x) is not None:
            result.type = AffixType.greater
            if x == "greateraffix2":
                result.value = float(matched_groups[x])
            break
    if matched_groups.get("onlyvalue") is not None:
        result.min_value = float(matched_groups.get("onlyvalue"))
        result.max_value = float(matched_groups.get("onlyvalue"))
    result.name = rapidfuzz.process.extractOne(
        keep_letters_and_spaces(_REPLACE_COMPARE_RE.sub("", result.text).strip()),
        list(Dataloader().affix_dict),
        scorer=rapidfuzz.distance.Levenshtein.distance,
    )[0]
    return result


def _has_numbers(affix_text):
    return any(char.isdigit() for char in affix_text)


# For unique aspects
def _get_aspect_from_text(text: str, name: str) -> Aspect:
    result = Aspect(text=text, name=name)
    for x in _AFFIX_REPLACEMENTS:
        text = text.replace(x, "")
    text = _REPLACE_COMPARE_RE.sub("", text).strip()

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


def read_descr_mixed(img_item_descr: np.ndarray) -> Item | None:
    tts_section = copy.copy(src.tts.LAST_ITEM)
    if not tts_section:
        return None
    if (item := _create_base_item_from_tts(tts_section)) is None:
        return None
    if any([
        is_consumable(item.item_type),
        is_non_sigil_mapping(item.item_type),
        is_sigil(item.item_type),
        is_socketable(item.item_type),
        item.item_type in [ItemType.Material, ItemType.Tribute],
    ]):
        return item
    if all([not is_armor(item.item_type), not is_jewelry(item.item_type), not is_weapon(item.item_type)]):
        return None

    if (sep_short_match := find_seperator_short(img_item_descr)) is None:
        LOGGER.warning("Could not detect item_seperator_short.")
        screenshot("failed_seperator_short", img=img_item_descr)
        return None
    futures = {
        "sep_long": TP.submit(find_seperators_long, img_item_descr, sep_short_match),
        "aspect_bullet": (
            TP.submit(find_aspect_bullet, img_item_descr, sep_short_match)
            if item.rarity in [ItemRarity.Legendary, ItemRarity.Unique, ItemRarity.Mythic]
            else None
        ),
    }

    affix_bullets = find_affix_bullets(img_item_descr, sep_short_match)

    if item.rarity == ItemRarity.Unique and item.name not in Dataloader().aspect_unique_dict:
        msg = (
            f"Unrecognized unique {item.name}. This most likely means the name of it reported "
            f"from Diablo 4 is wrong. Please report a bug with this message."
        )
        raise IndexError(msg)

    item.codex_upgrade = _is_codex_upgrade(tts_section)
    item.cosmetic_upgrade = _is_cosmetic_upgrade(tts_section)
    aspect_bullet = futures["aspect_bullet"].result() if futures["aspect_bullet"] else None
    return _add_affixes_from_tts_mixed(tts_section, item, affix_bullets, img_item_descr, aspect_bullet=aspect_bullet)


def read_descr() -> Item | None:
    tts_section = copy.copy(src.tts.LAST_ITEM)
    if not tts_section:
        return None
    if (item := _create_base_item_from_tts(tts_section)) is None:
        return None
    if is_sigil(item.item_type):
        return _add_sigil_affixes_from_tts(tts_section, item)
    if item.item_type == ItemType.Cosmetic:
        item.cosmetic_upgrade = True
        return item
    if any([
        is_consumable(item.item_type),
        is_non_sigil_mapping(item.item_type),
        is_socketable(item.item_type),
        item.item_type in [ItemType.Material, ItemType.Tribute, ItemType.Cache, ItemType.LairBossKey],
        item.sanctified,
    ]):
        return item

    if all([
        not is_armor(item.item_type),
        not is_jewelry(item.item_type),
        not is_weapon(item.item_type),
        item.item_type != ItemType.Shield,
    ]):
        return None

    if item.rarity not in [ItemRarity.Rare, ItemRarity.Legendary, ItemRarity.Mythic, ItemRarity.Unique]:
        return item

    if item.rarity == ItemRarity.Unique and item.name not in Dataloader().aspect_unique_dict:
        msg = f"Unrecognized unique {item.name}. This most likely means the name of it reported from Diablo 4 is wrong. Please report a bug with this message."
        raise IndexError(msg)

    item.codex_upgrade = _is_codex_upgrade(tts_section)
    item.cosmetic_upgrade = _is_cosmetic_upgrade(tts_section)
    return _add_affixes_from_tts(tts_section, item)
