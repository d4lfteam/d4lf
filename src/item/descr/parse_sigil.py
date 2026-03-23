from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType
from src.item.data.seasonal_attribute import SeasonalAttribute
from src.scripts import correct_name
from src.item.descr import keep_letters_and_spaces

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.item.models import Item

LOGGER = logging.getLogger(__name__)


def get_sigil_name_index(item: Item) -> int:
    return 3 if item.item_type == ItemType.EscalationSigil or item.seasonal_attribute == SeasonalAttribute.bloodied else 2


def extract_sigil_name(
    tts_section: list[str], item: Item, *, correct_name_func: Callable[[str], str] = correct_name
) -> str:
    name_index = get_sigil_name_index(item)
    name = tts_section[name_index].split(" in ")[0]
    return correct_name_func(name)


def _parse_sigil_affix_name(
    affix_name: str,
    *,
    correct_name_func: Callable[[str], str] = correct_name,
    keep_letters_and_spaces_func: Callable[[str], str] = keep_letters_and_spaces,
) -> str:
    return correct_name_func(keep_letters_and_spaces_func(affix_name))


def parse_sigil_affixes_from_tts(
    tts_section: list[str],
    item: Item,
    *,
    correct_name_func: Callable[[str], str] = correct_name,
    keep_letters_and_spaces_func: Callable[[str], str] = keep_letters_and_spaces,
) -> Item:
    item.name = extract_sigil_name(tts_section, item, correct_name_func=correct_name_func)

    start = next((i for i, s in enumerate(tts_section) if "AFFIXES" in s), None)
    if start is not None:
        first_affix_index = start + 1
        second_affix_index = start + 3
    else:
        LOGGER.error(
            "Could not find string AFFIXES in TTS provided by Diablo. Sigil filtering may be unstable, please open a bug with this info: %s",
            tts_section,
        )
        first_affix_index = 4
        second_affix_index = 6

    affixes = [tts_section[first_affix_index], tts_section[second_affix_index]]

    for affix_name in affixes:
        item.affixes.append(
            Affix(
                name=_parse_sigil_affix_name(
                    affix_name,
                    correct_name_func=correct_name_func,
                    keep_letters_and_spaces_func=keep_letters_and_spaces_func,
                ),
                type=AffixType.normal,
            )
        )

    return item
