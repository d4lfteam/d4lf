import copy
import logging
import re

import numpy as np
import rapidfuzz

import src.tts
from src import TP
from src.dataloader import Dataloader
from src.item.data.affix import Affix, AffixType
from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType, is_armor, is_consumable, is_jewelry, is_mapping, is_socketable, is_weapon
from src.item.data.rarity import ItemRarity
from src.item.descr import keep_letters_and_spaces
from src.item.descr.text import find_number
from src.item.descr.texture import find_affix_bullets, find_aspect_bullet, find_seperator_short, find_seperators_long
from src.item.models import Item
from src.template_finder import TemplateMatch
from src.utils.window import screenshot

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

_REPLACE_COMPARE_RE = re.compile(r"\(.*\)")

_AFFIX_REPLACEMENTS = ["%", "+", ",", "[+]", "[x]", "per 5 Seconds"]
LOGGER = logging.getLogger(__name__)


# Returns a tuple with the number of affixes.  It's in the format (inherent_num, affixes_num)
def _get_affix_counts(item: Item) -> (int, int):
    inherent_num = 0
    affixes_num = 3 if item.rarity == ItemRarity.Legendary else 4
    if is_weapon(item.item_type) or item.item_type in [ItemType.Amulet, ItemType.Boots]:
        inherent_num = 1
    elif item.item_type in [ItemType.Ring]:
        inherent_num = 2
    elif item.item_type in [ItemType.Shield]:
        inherent_num = 4

    if item.rarity in [ItemRarity.Unique, ItemRarity.Mythic] and item.item_type not in [ItemType.Shield]:
        # Uniques can have variable amounts of inherents. Sometimes we might not have a number for how many
        # inherents there are though and in that case we'll stick with the legendary default and hope for the best
        # Lidless wall, the only unique shield, doesn't count block chance as an inherent so we just use the legendary
        # default there too
        unique_inherents = Dataloader().aspect_unique_num_inherents.get(item.name)
        if unique_inherents is not None:
            inherent_num = unique_inherents

    return inherent_num, affixes_num


def _add_affixes_from_tts(tts_section: list[str], item: Item) -> Item:
    inherent_num, affixes_num = _get_affix_counts(item)

    affixes = _get_affixes_from_tts_section(tts_section, item, inherent_num + affixes_num)
    for i, affix_text in enumerate(affixes):
        if i < inherent_num:
            affix = _get_affix_from_text(affix_text)
            affix.type = AffixType.inherent
            item.inherent.append(affix)
        elif i < inherent_num + affixes_num:
            affix = _get_affix_from_text(affix_text)
            item.affixes.append(affix)
        else:
            if item.rarity == ItemRarity.Mythic:
                item.aspect = Aspect(
                    name=item.name,
                    text=affix_text,
                    value=find_number(affix_text),
                )
            else:
                item.aspect = _get_aspect_from_text(affix_text, item.name)
    return item


def _add_affixes_from_tts_mixed(
    tts_section: list[str],
    item: Item,
    affix_bullets: list[TemplateMatch],
    aspect_bullet: TemplateMatch | None,
) -> Item:
    # With advanced item compare on we'll actually find more bullets than we need, so we don't rely on them for number of affixes
    inherent_num, affixes_num = _get_affix_counts(item)

    affixes = _get_affixes_from_tts_section(
        tts_section,
        item,
        inherent_num + affixes_num,
    )

    if len(affixes) - 1 > len(affix_bullets):
        _raise_index_error(affixes, affix_bullets, item)

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
                item.aspect = Aspect(
                    name=item.name,
                    text=affix_text,
                    value=find_number(affix_text),
                )
            else:
                item.aspect = _get_aspect_from_text(affix_text, item.name)
            item.aspect.loc = aspect_bullet.center
    return item


def _raise_index_error(affixes, affix_bullets, item):
    LOGGER.error("About to raise index error, dumping information for debug:")
    LOGGER.error(f"Affixes ({len(affixes)}): {affixes}")
    LOGGER.error(f"Affix Bullets ({len(affix_bullets)}): {affix_bullets}")
    LOGGER.error(f"Item: {item}")

    raise IndexError(
        "Found more affixes than we found bullets to represent those affixes. This could be a temporary issue finding bullet positions on the screen, but if it happens consistently please open a bug report with a full screen screenshot with the item hovered on and vision mode disabled. Additionally, include the logs above this message."
    )


def _add_sigil_affixes_from_tts(tts_section: list[str], item: Item) -> Item:
    name = tts_section[2].split(" in ")[0]
    item.name = _correct_name(name)

    affixes = [tts_section[4], tts_section[6]]

    for affix_name in affixes:
        affix = Affix(name=_correct_name(keep_letters_and_spaces(affix_name)))
        affix.type = AffixType.normal
        item.affixes.append(affix)

    return item


def _create_base_item_from_tts(tts_item: list[str]) -> Item | None:
    if tts_item[0].startswith(src.tts.ItemIdentifiers.COMPASS.value):
        return Item(rarity=ItemRarity.Common, item_type=ItemType.Compass)
    if tts_item[0].startswith(src.tts.ItemIdentifiers.NIGHTMARE_SIGIL.value):
        return Item(rarity=ItemRarity.Common, item_type=ItemType.Sigil)
    if tts_item[0].startswith(src.tts.ItemIdentifiers.TRIBUTE.value):
        item = Item(item_type=ItemType.Tribute)
        search_string_split = tts_item[1].split(" ")
        item.rarity = _get_item_rarity(search_string_split[0])
        item.name = _correct_name(" ".join(search_string_split[1:]))
        return item
    if tts_item[0].startswith(src.tts.ItemIdentifiers.WHISPERING_KEY.value):
        return Item(item_type=ItemType.Consumable)
    if any(tts_item[1].lower().endswith(x) for x in ["summoning"]):
        return Item(item_type=ItemType.Material)
    if any(tts_item[1].lower().endswith(x) for x in ["gem"]):
        return Item(item_type=ItemType.Gem)
    if any(tts_item[1].lower().endswith(x) for x in ["cache"]):
        return Item(item_type=ItemType.Cache)
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
    if tts_item[1].lower().endswith("elixir"):
        item.item_type = ItemType.Elixir
    elif tts_item[1].lower().endswith("incense"):
        item.item_type = ItemType.Incense
    elif any(tts_item[1].lower().endswith(x) for x in ["consumable", "scroll"]):
        item.item_type = ItemType.Consumable
    if is_consumable(item.item_type):
        search_string_split = tts_item[1].split(" ")
        item.rarity = _get_item_rarity(search_string_split[0])
        return item

    search_string = tts_item[1].lower().replace("ancestral", "").strip()
    search_string_split = search_string.split(" ")
    item.rarity = _get_item_rarity(search_string_split[0])
    item.item_type = _get_item_type(" ".join(search_string_split[1:]))
    item.name = _correct_name(tts_item[0])
    for _i, line in enumerate(tts_item):
        if "item power" in line.lower():
            item.power = int(find_number(line))
            break
    return item


def _correct_name(name: str) -> str | None:
    if name:
        return name.lower().replace("'", "").replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")
    return name


def _get_affixes_from_tts_section(tts_section: list[str], item: Item, length: int):
    if item.rarity in [ItemRarity.Mythic, ItemRarity.Unique]:
        length += 1
    dps = None
    item_power = None
    masterwork = None
    armory = None
    start = 0
    for i, line in enumerate(tts_section):
        if "armory loadout" in line.lower():
            armory = i
        if "masterwork" in line.lower():
            masterwork = i
        if "item power" in line.lower():
            item_power = i
        if "damage per second" in line.lower():
            dps = i
            break  # this will always be the last line of the 4
    base_value = armory if armory else masterwork if masterwork else item_power
    if is_weapon(item.item_type):
        start = dps + 2
    elif is_jewelry(item.item_type):
        start = base_value
    elif is_armor(item.item_type):
        start = base_value + 1
    start += 1
    return tts_section[start : start + length]


def _get_affix_from_text(text: str) -> Affix:
    result = Affix(text=text)
    for x in _AFFIX_REPLACEMENTS:
        text = text.replace(x, "")
    text = _REPLACE_COMPARE_RE.sub("", text).strip()

    # A hacky way to make lucky hit chance to make vulnerable work. Hoping Chris saves me from myself on this one one day
    if "Lucky Hit" in text and "Vulnerable" in text:
        for x in ["Make Enemies Vulnerable for 2 Seconds", "[2]"]:
            text = text.replace(x, "")
    elif "for 4 Seconds" in text and "Blood Orb" in text:
        for x in ["for 4 Seconds", "[4]"]:
            text = text.replace(x, "")
    elif "for 7 Seconds" in text and "After Killing an Elite" in text:
        for x in ["for 7 Seconds", "[7]"]:
            text = text.replace(x, "")

    matched_groups = {}
    for match in _AFFIX_RE.finditer(text):
        matched_groups = {name: value for name, value in match.groupdict().items() if value is not None}
    if not matched_groups and _has_numbers(text):
        raise Exception(f"Could not match affix text: {text}")
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
        keep_letters_and_spaces(result.text), list(Dataloader().affix_dict), scorer=rapidfuzz.distance.Levenshtein.distance
    )[0]
    return result


def _has_numbers(affix_text):
    return any(char.isdigit() for char in affix_text)


def _get_aspect_from_text(text: str, name: str) -> Aspect:
    result = Aspect(text=text, name=name)
    for x in _AFFIX_REPLACEMENTS:
        text = text.replace(x, "")
    text = _REPLACE_COMPARE_RE.sub("", text).strip()

    match = _ASPECT_RE.search(text)
    if match:  # No match means the aspect is text only, there are no values to filter on
        matched_groups = {name: value for name, value in match.groupdict().items() if value is not None}
        if not matched_groups:
            raise Exception(f"Could not match aspect text: {text}")

        if matched_groups.get("minvalue") is not None:
            result.min_value = float(matched_groups["minvalue"])
        if matched_groups.get("maxvalue") is not None:
            result.max_value = float(matched_groups["maxvalue"])
        if matched_groups.get("affixvalue") is not None:
            result.value = float(matched_groups["affixvalue"])

    return result


def _get_item_rarity(data: str) -> ItemRarity | None:
    res = rapidfuzz.process.extractOne(data, [rar.value for rar in ItemRarity], scorer=rapidfuzz.distance.Levenshtein.distance)
    try:
        return ItemRarity(res[0]) if res else None
    except ValueError:
        return None


def _get_item_type(data: str):
    res = rapidfuzz.process.extractOne(data, [it.value for it in ItemType], scorer=rapidfuzz.distance.Levenshtein.distance)
    try:
        return ItemType(res[0]) if res else None
    except ValueError:
        return None


def _is_codex_upgrade(tts_section: list[str]) -> bool:
    return any("upgrades an aspect in the codex of power" in line.lower() or "unlocks new aspect" in line.lower() for line in tts_section)


def _is_cosmetic_upgrade(tts_section: list[str]):
    return any("unlocks new look on salvage" in line.lower() for line in tts_section)


def read_descr_mixed(img_item_descr: np.ndarray) -> Item | None:
    tts_section = copy.copy(src.tts.LAST_ITEM)
    if not tts_section:
        return None
    if (item := _create_base_item_from_tts(tts_section)) is None:
        return None
    if any(
        [
            is_consumable(item.item_type),
            is_mapping(item.item_type),
            is_socketable(item.item_type),
            item.item_type in [ItemType.Material, ItemType.Tribute],
        ]
    ):
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

    item.codex_upgrade = _is_codex_upgrade(tts_section)
    item.cosmetic_upgrade = _is_cosmetic_upgrade(tts_section)
    aspect_bullet = futures["aspect_bullet"].result() if futures["aspect_bullet"] is not None else None
    return _add_affixes_from_tts_mixed(tts_section, item, affix_bullets, aspect_bullet=aspect_bullet)


def read_descr() -> Item | None:
    tts_section = copy.copy(src.tts.LAST_ITEM)
    if not tts_section:
        return None
    if (item := _create_base_item_from_tts(tts_section)) is None:
        return None
    if item.item_type == ItemType.Sigil:
        return _add_sigil_affixes_from_tts(tts_section, item)
    if item.item_type == ItemType.Cosmetic:
        item.cosmetic_upgrade = True
        return item
    if any(
        [
            is_consumable(item.item_type),
            is_mapping(item.item_type),
            is_socketable(item.item_type),
            item.item_type in [ItemType.Material, ItemType.Tribute, ItemType.Cache, ItemType.LairBossKey],
        ]
    ):
        return item

    if all(
        [not is_armor(item.item_type), not is_jewelry(item.item_type), not is_weapon(item.item_type), item.item_type != ItemType.Shield]
    ):
        return None
    if item.rarity not in [ItemRarity.Legendary, ItemRarity.Mythic, ItemRarity.Unique]:
        return item

    item.codex_upgrade = _is_codex_upgrade(tts_section)
    item.cosmetic_upgrade = _is_cosmetic_upgrade(tts_section)
    return _add_affixes_from_tts(tts_section, item)
