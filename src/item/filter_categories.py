import logging

from src.item.data.item_type import is_sigil
from src.item.data.rarity import ItemRarity
from src.item.filter_types import FilterResult, MatchedFilter

LOGGER = logging.getLogger(__name__)


def evaluate_sigil(item, sigil_filters, match_affixes_sigils_func) -> FilterResult:
    res = FilterResult(False, [])
    if not sigil_filters.items():
        LOGGER.info(f"{item.original_name} -- Matched Sigils")
        res.keep = True
        res.matched.append(MatchedFilter("Sigils not filtered"))

    for profile_name, profile_filter in sigil_filters.items():
        blacklist_empty = not profile_filter.blacklist
        is_in_blacklist = match_affixes_sigils_func(
            expected_affixes=profile_filter.blacklist,
            sigil_name=item.name,
            sigil_affixes=item.affixes + item.inherent,
        )
        blacklist_ok = True if blacklist_empty else not is_in_blacklist
        whitelist_empty = not profile_filter.whitelist
        is_in_whitelist = match_affixes_sigils_func(
            expected_affixes=profile_filter.whitelist,
            sigil_name=item.name,
            sigil_affixes=item.affixes + item.inherent,
        )
        whitelist_ok = True if whitelist_empty else is_in_whitelist

        if (blacklist_empty and not whitelist_empty and not whitelist_ok) or (
            whitelist_empty and not blacklist_empty and not blacklist_ok
        ):
            continue
        if not blacklist_empty and not whitelist_empty:
            if not blacklist_ok and not whitelist_ok:
                continue
            if is_in_blacklist and is_in_whitelist:
                if profile_filter.priority.value == "whitelist" and not whitelist_ok:
                    continue
                if profile_filter.priority.value == "blacklist" and not blacklist_ok:
                    continue
            elif (is_in_blacklist and not blacklist_ok) or (not is_in_whitelist and not whitelist_ok):
                continue
        LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Sigils")
        res.keep = True
        res.matched.append(MatchedFilter(f"{profile_name}"))
    return res


def evaluate_tribute(item, tribute_filters) -> FilterResult:
    res = FilterResult(False, [])
    if not tribute_filters.items():
        LOGGER.info(f"{item.original_name} -- Matched Tributes")
        res.keep = True
        res.matched.append(MatchedFilter("Tributes not filtered"))

    if item.rarity == ItemRarity.Mythic:
        LOGGER.info(f"{item.original_name} -- Matched mythic tribute, always kept")
        res.keep = True
        res.matched.append(MatchedFilter("Mythic Tribute"))

    for profile_name, profile_filter in tribute_filters.items():
        for filter_item in profile_filter:
            if filter_item.name and not item.name.startswith(filter_item.name):
                continue
            if filter_item.rarities and item.rarity not in filter_item.rarities:
                continue

            LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Tributes")
            res.keep = True
            res.matched.append(MatchedFilter(f"{profile_name}"))
    return res
