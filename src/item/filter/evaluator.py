"""Pure item-rule evaluation over loaded rules and immutable settings."""

import logging
from dataclasses import replace
from typing import TYPE_CHECKING, override

from src.game_data import ItemRarity, ItemType, is_sigil
from src.item import MYTHICS_ALWAYS_KEPT_LABEL
from src.item.filter.equipment import FilterEquipmentMixin
from src.item.filter.matching import FilterContext, FilterMatchingMixin
from src.item.filter.rules import EvaluationSettings, LoadedRules
from src.item.filter.special import FilterSpecialMixin
from src.item.models import FilterResult, MatchedFilter

if TYPE_CHECKING:
    from collections.abc import Mapping

    from src.item.models import Item
    from src.profiles import (
        DynamicCharmFilterModel,
        DynamicItemFilterModel,
        DynamicSealFilterModel,
        GlobalUniqueModel,
        ParagonPayloadModel,
        SigilFilterModel,
        TributeFilterModel,
    )

LOGGER = logging.getLogger(__name__)


class FilterEvaluator(FilterSpecialMixin, FilterEquipmentMixin, FilterMatchingMixin, FilterContext):
    """Evaluate one item against a complete rules and settings snapshot."""

    def __init__(
        self,
        rules: LoadedRules | None = None,
        evaluation_settings: EvaluationSettings | None = None,
    ) -> None:
        self._rules = rules or LoadedRules.empty()
        self._evaluation_settings = evaluation_settings or EvaluationSettings()

    @property
    @override
    def rules(self) -> LoadedRules:
        return self._rules

    @rules.setter
    @override
    def rules(self, value: LoadedRules) -> None:
        self._rules = value

    @property
    @override
    def evaluation_settings(self) -> EvaluationSettings:
        return self._evaluation_settings

    @evaluation_settings.setter
    @override
    def evaluation_settings(self, value: EvaluationSettings) -> None:
        self._evaluation_settings = value

    @property
    @override
    def affix_filters(self) -> Mapping[str, list[DynamicItemFilterModel]]:
        return self._rules.affix_filters

    @affix_filters.setter
    @override
    def affix_filters(self, value: Mapping[str, list[DynamicItemFilterModel]]) -> None:
        self.rules = replace(self._rules, affix_filters=value)

    @property
    @override
    def aspect_upgrade_filters(self) -> Mapping[str, list[str]]:
        return self._rules.aspect_upgrade_filters

    @aspect_upgrade_filters.setter
    @override
    def aspect_upgrade_filters(self, value: Mapping[str, list[str]]) -> None:
        self.rules = replace(self._rules, aspect_upgrade_filters=value)

    @property
    @override
    def paragon_filters(self) -> Mapping[str, ParagonPayloadModel]:
        return self._rules.paragon_filters

    @paragon_filters.setter
    @override
    def paragon_filters(self, value: Mapping[str, ParagonPayloadModel]) -> None:
        self.rules = replace(self._rules, paragon_filters=value)

    @property
    @override
    def global_unique_filters(self) -> Mapping[str, list[GlobalUniqueModel]]:
        return self._rules.global_unique_filters

    @global_unique_filters.setter
    @override
    def global_unique_filters(self, value: Mapping[str, list[GlobalUniqueModel]]) -> None:
        self.rules = replace(self._rules, global_unique_filters=value)

    @property
    @override
    def seal_filters(self) -> Mapping[str, list[DynamicSealFilterModel]]:
        return self._rules.seal_filters

    @seal_filters.setter
    @override
    def seal_filters(self, value: Mapping[str, list[DynamicSealFilterModel]]) -> None:
        self.rules = replace(self._rules, seal_filters=value)

    @property
    @override
    def charm_filters(self) -> Mapping[str, list[DynamicCharmFilterModel]]:
        return self._rules.charm_filters

    @charm_filters.setter
    @override
    def charm_filters(self, value: Mapping[str, list[DynamicCharmFilterModel]]) -> None:
        self.rules = replace(self._rules, charm_filters=value)

    @property
    @override
    def sigil_filters(self) -> Mapping[str, SigilFilterModel]:
        return self._rules.sigil_filters

    @sigil_filters.setter
    @override
    def sigil_filters(self, value: Mapping[str, SigilFilterModel]) -> None:
        self.rules = replace(self._rules, sigil_filters=value)

    @property
    @override
    def tribute_filters(self) -> Mapping[str, TributeFilterModel]:
        return self._rules.tribute_filters

    @tribute_filters.setter
    @override
    def tribute_filters(self, value: Mapping[str, TributeFilterModel]) -> None:
        self.rules = replace(self._rules, tribute_filters=value)

    def _skipped_by_filter_override(self, item: Item) -> bool:
        settings = self.evaluation_settings
        if is_sigil(item.item_type):
            return not settings.filter_sigils
        if item.item_type == ItemType.Tribute:
            return not settings.filter_tributes
        if item.item_type == ItemType.HoradricSeal:
            return not settings.filter_seals
        if item.item_type == ItemType.Charm:
            return not settings.filter_charms
        if item.item_type is None or item.power is None:
            return False
        return not settings.filter_equipment

    def should_keep(self, item: Item) -> FilterResult:
        """Return the keep decision without reading mutable application state."""
        if self._skipped_by_filter_override(item):
            LOGGER.debug("%s -- Skipped by loot filter override", item.original_name)
            return FilterResult(keep=False, matched=[], skipped=True)
        result = FilterResult(keep=False, matched=[])
        if is_sigil(item.item_type):
            return self._check_sigil(item)
        if item.item_type == ItemType.Tribute:
            return self._check_tribute(item)
        if item.item_type == ItemType.HoradricSeal:
            return self._check_seal_charm_filters(item, self.seal_filters, "Seals", "Mythic Seal")
        if item.item_type == ItemType.Charm:
            return self._check_seal_charm_filters(item, self.charm_filters, "Charms", "Mythic Charm")
        if item.item_type is None or item.power is None:
            return result
        keep_affixes = self._check_affixes(item)
        if keep_affixes.keep:
            return keep_affixes
        if item.rarity == ItemRarity.Legendary:
            result = self._check_aspect_upgrades(item)
        elif item.rarity == ItemRarity.Unique:
            result = self._check_global_unique_filter(item)
        elif item.rarity == ItemRarity.Mythic:
            result = FilterResult(keep=True, matched=[MatchedFilter(profile=MYTHICS_ALWAYS_KEPT_LABEL, aspect_match=True)])
        if not result.keep:
            return self._check_cosmetic(item)
        return result

    def evaluate(self, item: Item) -> FilterResult:
        """Alias emphasizing that this module performs a pure evaluation."""
        return self.should_keep(item)
