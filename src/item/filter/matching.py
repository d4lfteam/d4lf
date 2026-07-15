import sys
from typing import TYPE_CHECKING, Any

from src.item.data.affix import Affix, AffixType
from src.item.data.aspect import Aspect  # noqa: TC001
from src.item.data.item_type import ItemType  # noqa: TC001
from src.item.data.rarity import ItemRarity

if TYPE_CHECKING:
    from src.config.profile_models import (
        AffixAspectFilterModel,
        AffixFilterCountModel,
        AffixFilterModel,
        AspectUniqueFilterModel,
    )
    from src.item.models import Item


class FilterContext:
    def __getattr__(self, name: str) -> Any:
        raise AttributeError(name)


class FilterMatchingMixin:
    def _check_unique_aspects_for_item(self, item: Item, unique_aspects: list[AspectUniqueFilterModel]) -> bool:
        matched_unique_aspect = None  # model enforces aspect-name uniqueness
        for unique_aspect in unique_aspects:
            if self._match_item_aspect_or_affix(expected_aspect=unique_aspect, item_aspect=item.aspect):
                matched_unique_aspect = unique_aspect
                break
        if unique_aspects and not matched_unique_aspect:
            return False
        if item.rarity in [ItemRarity.Unique, ItemRarity.Mythic] and not matched_unique_aspect:  # don't check affixes
            return False
        if matched_unique_aspect is None:
            return True
        if item.aspect is None:
            return False
        return self._match_item_roll_is_in_percent_range(
            expected_percent=matched_unique_aspect.min_percent_of_aspect, item_aspect_or_affix=item.aspect
        )

    def _match_affixes_count(
        self, expected_affixes: list[AffixFilterCountModel], item_affixes: list[Affix], min_greater_affix_count: int = 0
    ) -> list[Affix]:
        result = []
        for count_group in expected_affixes:
            group_res = []
            for affix in count_group.count:
                matched_item_affix = next((a for a in item_affixes if a.name == affix.name), None)
                if matched_item_affix is not None and self._match_item_aspect_or_affix(affix, matched_item_affix):
                    group_res.append(matched_item_affix)

            if not (count_group.min_count <= len(group_res) <= count_group.max_count):
                return []

            want_greater_affixes = [a for a in count_group.count if getattr(a, "want_greater", False)]
            want_greater_count = len(want_greater_affixes)
            if want_greater_count > 0 and min_greater_affix_count > 0:
                if min_greater_affix_count > want_greater_count:  # all flagged affixes must be GAs
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
                    if flagged_ga_count < min_greater_affix_count:  # not enough flagged affixes are GAs
                        return []
            result.extend(group_res)
        return result

    def _match_affixes_uniques(
        self, expected_affixes: list[AffixFilterModel], item_affixes: list[Affix], min_greater_affix_count: int = 0
    ) -> bool:
        for expected_affix in expected_affixes:
            matched_item_affix = next((a for a in item_affixes if a.name == expected_affix.name), None)
            if matched_item_affix is None or not self._match_item_aspect_or_affix(expected_affix, matched_item_affix):
                return False

        want_greater_affixes = [a for a in expected_affixes if getattr(a, "want_greater", False)]
        want_greater_count = len(want_greater_affixes)
        if want_greater_count > 0 and min_greater_affix_count > 0:
            if min_greater_affix_count > want_greater_count:  # all flagged affixes must be GAs
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
                if flagged_ga_count < min_greater_affix_count:  # not enough flagged affixes are GAs
                    return False
        return True

    @staticmethod
    def _match_greater_affix_count(expected_min_count: int, item_affixes: list[Affix]) -> bool:
        return expected_min_count <= len([x for x in item_affixes if x.type == AffixType.greater])

    @staticmethod
    def _match_item_roll_is_in_percent_range(expected_percent: int, item_aspect_or_affix: Aspect | Affix) -> bool:
        min_value = item_aspect_or_affix.min_value
        max_value = item_aspect_or_affix.max_value
        value = item_aspect_or_affix.value
        if expected_percent == 0 or max_value is None or min_value is None:
            return True
        if value is None:
            return False
        if max_value == min_value:
            return True
        if not FilterMatchingMixin._is_smaller_roll_better(item_aspect_or_affix):
            percent_float = expected_percent / 100.0
            return (value - min_value) / (max_value - min_value) >= percent_float
        percent_float = (100 - expected_percent) / 100.0
        return (value - max_value) / (min_value - max_value) <= percent_float

    @staticmethod
    def _is_smaller_roll_better(item_aspect_or_affix: Aspect | Affix) -> bool:
        return (
            item_aspect_or_affix.max_value is not None
            and item_aspect_or_affix.min_value is not None
            and item_aspect_or_affix.max_value < item_aspect_or_affix.min_value
        )

    @staticmethod
    def _match_item_value_threshold(expected_value: float, item_aspect_or_affix: Aspect | Affix) -> bool:
        if item_aspect_or_affix.value is None:
            return False
        if FilterMatchingMixin._is_smaller_roll_better(item_aspect_or_affix):
            return item_aspect_or_affix.value <= expected_value
        return item_aspect_or_affix.value >= expected_value

    def _match_item_aspect_or_affix(
        self,
        expected_aspect: AffixAspectFilterModel | None,
        item_aspect: Aspect | Affix | None,
        is_fixed_aspect_value: bool = False,
    ) -> bool:
        if expected_aspect is None:
            return True
        if item_aspect is None or expected_aspect.name != item_aspect.name:
            return False
        if expected_aspect.value is not None:
            if item_aspect.value is None:  # fixed aspect values are always at max
                return bool(is_fixed_aspect_value)
            if not self._match_item_value_threshold(expected_aspect.value, item_aspect):
                return False
        expected_affix_percent = getattr(expected_aspect, "min_percent_of_affix", 0)
        if expected_affix_percent:
            if isinstance(item_aspect, Affix) and item_aspect.type == AffixType.greater:
                return True
            if not self._match_item_roll_is_in_percent_range(expected_affix_percent, item_aspect):
                return False
        return True

    @staticmethod
    def _match_item_power(min_power: int, item_power: int | None, max_power: int = sys.maxsize) -> bool:
        if item_power is None:
            return False
        return min_power <= item_power <= max_power

    @staticmethod
    def _match_item_type(expected_item_types: list[ItemType], item_type: ItemType | None) -> bool:
        if not expected_item_types:
            return True
        return item_type in expected_item_types
