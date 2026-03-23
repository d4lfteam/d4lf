import sys
from typing import TYPE_CHECKING

from src.config.models import AffixAspectFilterModel, AffixFilterCountModel, AffixFilterModel, ComparisonType, SigilConditionModel
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType

if TYPE_CHECKING:
    from src.item.data.aspect import Aspect


def match_affixes_count(
    expected_affixes: list[AffixFilterCountModel],
    item_affixes: list[Affix],
    min_greater_affix_count: int,
    match_item_aspect_or_affix_func,
) -> list[Affix]:
    result = []
    for count_group in expected_affixes:
        group_res = []

        for affix in count_group.count:
            matched_item_affix = next((a for a in item_affixes if a.name == affix.name), None)
            if matched_item_affix is not None and match_item_aspect_or_affix_func(affix, matched_item_affix):
                group_res.append(matched_item_affix)

        if not (count_group.minCount <= len(group_res) <= count_group.maxCount):
            return []

        want_greater_affixes = [a for a in count_group.count if getattr(a, "want_greater", False)]
        want_greater_count = len(want_greater_affixes)

        if want_greater_count > 0 and min_greater_affix_count > 0:
            if min_greater_affix_count > want_greater_count:
                for affix in want_greater_affixes:
                    matched_item_affix = next((a for a in item_affixes if a.name == affix.name), None)
                    if matched_item_affix is None or matched_item_affix.type != AffixType.greater:
                        return []
            else:
                flagged_ga_count = sum(
                    1
                    for affix in want_greater_affixes
                    if (matched := next((a for a in item_affixes if a.name == affix.name), None))
                    and matched.type == AffixType.greater
                )
                if flagged_ga_count < min_greater_affix_count:
                    return []

        result.extend(group_res)
    return result


def match_affixes_sigils(
    expected_affixes: list[SigilConditionModel], sigil_name: str, sigil_affixes: list[Affix]
) -> bool:
    for expected_affix in expected_affixes:
        if sigil_name != expected_affix.name and not [affix for affix in sigil_affixes if affix.name == expected_affix.name]:
            continue
        if expected_affix.condition and not any(affix.name in expected_affix.condition for affix in sigil_affixes):
            continue
        return True
    return False


def match_affixes_uniques(
    expected_affixes: list[AffixFilterModel],
    item_affixes: list[Affix],
    min_greater_affix_count: int,
    match_item_aspect_or_affix_func,
) -> bool:
    for expected_affix in expected_affixes:
        matched_item_affix = next((a for a in item_affixes if a.name == expected_affix.name), None)
        if matched_item_affix is None or not match_item_aspect_or_affix_func(expected_affix, matched_item_affix):
            return False

    want_greater_affixes = [a for a in expected_affixes if getattr(a, "want_greater", False)]
    want_greater_count = len(want_greater_affixes)

    if want_greater_count > 0 and min_greater_affix_count > 0:
        if min_greater_affix_count > want_greater_count:
            for affix in want_greater_affixes:
                matched_item_affix = next((a for a in item_affixes if a.name == affix.name), None)
                if matched_item_affix is None or matched_item_affix.type != AffixType.greater:
                    return False
        else:
            flagged_ga_count = sum(
                1
                for affix in want_greater_affixes
                if (matched := next((a for a in item_affixes if a.name == affix.name), None))
                and matched.type == AffixType.greater
            )
            if flagged_ga_count < min_greater_affix_count:
                return False

    return True


def match_greater_affix_count(expected_min_count: int, item_affixes: list[Affix]) -> bool:
    return expected_min_count <= len([x for x in item_affixes if x.type == AffixType.greater])


def match_aspect_is_in_percent_range(expected_percent: int, item_aspect: "Aspect") -> bool:
    if expected_percent == 0 or item_aspect.max_value is None or item_aspect.min_value is None:
        return True

    if item_aspect.max_value > item_aspect.min_value:
        percent_float = expected_percent / 100.0
        return (item_aspect.value - item_aspect.min_value) / (item_aspect.max_value - item_aspect.min_value) >= percent_float

    percent_float = (100 - expected_percent) / 100.0
    return (item_aspect.value - item_aspect.max_value) / (item_aspect.min_value - item_aspect.max_value) <= percent_float


def match_item_aspect_or_affix(
    expected_aspect: AffixAspectFilterModel | None,
    item_aspect: "Aspect | Affix",
    is_fixed_aspect_value: bool = False,
) -> bool:
    if expected_aspect is None:
        return True
    if expected_aspect.name != item_aspect.name:
        return False

    if expected_aspect.value is not None:
        if item_aspect.value is None:
            return bool(is_fixed_aspect_value)
        if (expected_aspect.comparison == ComparisonType.larger and item_aspect.value < expected_aspect.value) or (
            expected_aspect.comparison == ComparisonType.smaller and item_aspect.value > expected_aspect.value
        ):
            return False
    return True


def match_item_power(min_power: int, item_power: int, max_power: int = sys.maxsize) -> bool:
    return min_power <= item_power <= max_power


def match_item_type(expected_item_types: list[ItemType], item_type: ItemType) -> bool:
    if not expected_item_types:
        return True
    return item_type in expected_item_types
