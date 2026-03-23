from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.config.models import AffixFilterModel, UnfilteredUniquesType
from src.item.data.affix import Affix
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.data.seasonal_attribute import SeasonalAttribute
from src.item.filter_matchers import (
    match_affixes_uniques,
    match_aspect_is_in_percent_range,
    match_greater_affix_count,
    match_item_aspect_or_affix,
    match_item_power,
    match_item_type,
)
from src.item.filter_types import FilterResult, MatchedFilter

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.item.data.aspect import Aspect
    from src.item.models import Item

LOGGER = logging.getLogger(__name__)


def evaluate_unique_item(
    item: Item,
    unique_filters: dict[str, list],
    handle_uniques: UnfilteredUniquesType,
    *,
    match_item_type_func: Callable[[list[ItemType], ItemType], bool] = match_item_type,
    match_item_power_func: Callable[[int, int, int], bool] = match_item_power,
    match_item_aspect_or_affix_func: Callable[[AffixFilterModel | None, Aspect | Affix, bool], bool] = (
        match_item_aspect_or_affix
    ),
    match_affixes_uniques_func: Callable[[list[AffixFilterModel], list[Affix], int, Callable[..., bool]], bool] = (
        match_affixes_uniques
    ),
    match_greater_affix_count_func: Callable[[int, list[Affix]], bool] = match_greater_affix_count,
    match_aspect_is_in_percent_range_func: Callable[[int, Aspect], bool] = match_aspect_is_in_percent_range,
) -> FilterResult:
    res = FilterResult(False, [])
    all_filters_are_aspect = True

    if not unique_filters:
        keep = handle_uniques != UnfilteredUniquesType.junk or item.rarity == ItemRarity.Mythic
        return FilterResult(keep, [])

    for profile_name, profile_filter in unique_filters.items():
        for filter_item in profile_filter:
            if not filter_item.aspect:
                all_filters_are_aspect = False
            elif item.aspect and filter_item.aspect.name == item.aspect.name:
                res.unique_aspect_in_profile = True

            if filter_item.mythic and item.rarity != ItemRarity.Mythic:
                continue
            if not match_item_type_func(expected_item_types=filter_item.itemType, item_type=item.item_type):
                continue
            if not match_item_power_func(min_power=filter_item.minPower, item_power=item.power):
                continue
            if not match_item_aspect_or_affix_func(
                filter_item.aspect,
                item.aspect,
                item.seasonal_attribute == SeasonalAttribute.bloodied,
            ):
                continue
            if not match_affixes_uniques_func(
                expected_affixes=filter_item.affix,
                item_affixes=item.affixes,
                min_greater_affix_count=filter_item.minGreaterAffixCount,
                match_item_aspect_or_affix_func=match_item_aspect_or_affix_func,
            ):
                continue
            if not match_greater_affix_count_func(
                expected_min_count=filter_item.minGreaterAffixCount,
                item_affixes=item.affixes,
            ):
                continue
            if not match_aspect_is_in_percent_range_func(
                expected_percent=filter_item.minPercentOfAspect,
                item_aspect=item.aspect,
            ):
                continue

            LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Uniques: {item.aspect.name}")
            res.keep = True
            matched_full_name = f"{profile_name}.{item.aspect.name}"
            if filter_item.profileAlias:
                matched_full_name = f"{filter_item.profileAlias}.{item.aspect.name}"
            res.matched.append(MatchedFilter(matched_full_name, did_match_aspect=True))

    res.all_unique_filters_are_aspects = all_filters_are_aspect

    if not res.keep and (
        item.rarity == ItemRarity.Mythic
        or (
            res.all_unique_filters_are_aspects
            and not res.unique_aspect_in_profile
            and handle_uniques != UnfilteredUniquesType.junk
        )
    ):
        res.keep = True

    return res
