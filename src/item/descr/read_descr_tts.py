import copy
import logging
from typing import TYPE_CHECKING

import src.tts
from src import TP
from src.dataloader import Dataloader
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
from src.item.data.seasonal_attribute import SeasonalAttribute
from src.item.descr.parse_affixes import add_affixes_from_tts, add_affixes_from_tts_mixed
from src.item.descr.parse_aspect import parse_aspect_from_tts_section
from src.item.descr.parse_base_item import create_base_item_from_tts
from src.item.descr.parse_sigil import parse_sigil_affixes_from_tts
from src.item.descr.texture import find_affix_bullets, find_aspect_bullet, find_seperator_short, find_seperators_long
from src.item.models import Item
from src.utils.window import screenshot

if TYPE_CHECKING:
    import numpy as np

LOGGER = logging.getLogger(__name__)


def _is_codex_upgrade(tts_section: list[str]) -> bool:
    return any(
        "upgrades an aspect in the codex of power" in line.lower() or "unlocks new aspect" in line.lower()
        for line in tts_section
    )


def _is_cosmetic_upgrade(tts_section: list[str]) -> bool:
    return any("unlocks new look on salvage" in line.lower() for line in tts_section)


def read_descr_mixed(img_item_descr: np.ndarray) -> Item | None:
    tts_section = copy.copy(src.tts.LAST_ITEM)
    if not tts_section:
        return None
    if (item := create_base_item_from_tts(tts_section)) is None:
        return None
    if any(
        [
            is_consumable(item.item_type),
            is_non_sigil_mapping(item.item_type),
            is_sigil(item.item_type),
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

    if item.rarity == ItemRarity.Unique and item.name not in Dataloader().aspect_unique_dict:
        msg = (
            f"Unrecognized unique {item.name}. This most likely means the name of it reported "
            f"from Diablo 4 is wrong. Please report a bug with this message."
        )
        raise IndexError(msg)

    item.codex_upgrade = _is_codex_upgrade(tts_section)
    item.cosmetic_upgrade = _is_cosmetic_upgrade(tts_section)
    aspect_bullet = futures["aspect_bullet"].result() if futures["aspect_bullet"] else None
    return add_affixes_from_tts_mixed(
        tts_section,
        item,
        affix_bullets,
        img_item_descr,
        aspect_bullet=aspect_bullet,
        parse_aspect_func=parse_aspect_from_tts_section,
    )


def read_descr() -> Item | None:
    tts_section = copy.copy(src.tts.LAST_ITEM)
    if not tts_section:
        return None
    if (item := create_base_item_from_tts(tts_section)) is None:
        return None
    if is_sigil(item.item_type):
        return parse_sigil_affixes_from_tts(tts_section, item)
    if item.item_type == ItemType.Cosmetic:
        item.cosmetic_upgrade = True
        return item
    if any(
        [
            is_consumable(item.item_type),
            is_non_sigil_mapping(item.item_type),
            is_socketable(item.item_type),
            item.item_type in [ItemType.Material, ItemType.Tribute, ItemType.Cache, ItemType.LairBossKey],
            item.seasonal_attribute == SeasonalAttribute.sanctified,
        ]
    ):
        return item

    if all(
        [
            not is_armor(item.item_type),
            not is_jewelry(item.item_type),
            not is_weapon(item.item_type),
            item.item_type != ItemType.Shield,
        ]
    ):
        return None

    if item.rarity not in [ItemRarity.Rare, ItemRarity.Legendary, ItemRarity.Mythic, ItemRarity.Unique]:
        return item
    if item.rarity == ItemRarity.Mythic and item.is_in_shop:
        return None

    if item.rarity in [ItemRarity.Unique, ItemRarity.Mythic] and item.name not in Dataloader().aspect_unique_dict:
        msg = (
            f"Unrecognized unique {item.name}. This most likely means the name of it reported "
            f"from Diablo 4 is wrong. Please report a bug with this message. TTS: {tts_section}"
        )
        raise IndexError(msg)

    item.codex_upgrade = _is_codex_upgrade(tts_section)
    item.cosmetic_upgrade = _is_cosmetic_upgrade(tts_section)
    return add_affixes_from_tts(tts_section, item, parse_aspect_func=parse_aspect_from_tts_section)
