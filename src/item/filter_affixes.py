import logging
from typing import TYPE_CHECKING

from src.config.models import DynamicItemFilterModel
from src.item.data.affix import Affix, AffixType
from src.item.filter_matchers import (
    match_affixes_count,
    match_greater_affix_count,
    match_item_aspect_or_affix,
    match_item_power,
    match_item_type,
)
from src.item.filter_types import FilterResult, MatchedFilter

if TYPE_CHECKING:
    from src.item.models import Item

LOGGER = logging.getLogger(__name__)


def _match_details(matched_affixes: list[Affix]) -> list[str]:
    details: list[str] = []
    for affix in matched_affixes:
        if affix.type == AffixType.greater:
            details.append(f"{affix.name} (GA)")
        else:
            details.append(affix.name)
    return details


def evaluate_affix_profiles(item: "Item", affix_filters: dict[str, list[DynamicItemFilterModel]]) -> FilterResult:
    res = FilterResult(False, [])
    if not affix_filters:
        return FilterResult(True, [])

    non_tempered_affixes = [affix for affix in item.affixes if affix.type != AffixType.tempered]
    for profile_name, profile_filter in affix_filters.items():
        for filter_item in profile_filter:
            filter_name = next(iter(filter_item.root.keys()))
            filter_spec = filter_item.root[filter_name]
            if not match_item_type(expected_item_types=filter_spec.itemType, item_type=item.item_type):
                continue
            if not match_item_power(min_power=filter_spec.minPower, item_power=item.power):
                continue
            if not match_greater_affix_count(
                expected_min_count=filter_spec.minGreaterAffixCount, item_affixes=non_tempered_affixes
            ):
                continue

            matched_affixes: list[Affix] = []
            if filter_spec.affixPool:
                matched_affixes = match_affixes_count(
                    expected_affixes=filter_spec.affixPool,
                    item_affixes=non_tempered_affixes,
                    min_greater_affix_count=filter_spec.minGreaterAffixCount,
                    match_item_aspect_or_affix_func=match_item_aspect_or_affix,
                )
                if not matched_affixes:
                    continue

            matched_inherents: list[Affix] = []
            if filter_spec.inherentPool:
                matched_inherents = match_affixes_count(
                    expected_affixes=filter_spec.inherentPool,
                    item_affixes=item.inherent,
                    min_greater_affix_count=filter_spec.minGreaterAffixCount,
                    match_item_aspect_or_affix_func=match_item_aspect_or_affix,
                )
                if not matched_inherents:
                    continue

            all_matches = matched_affixes + matched_inherents
            LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Affixes.{filter_name}: {_match_details(all_matches)}")
            res.keep = True
            res.matched.append(MatchedFilter(f"{profile_name}.{filter_name}", all_matches))
    return res
