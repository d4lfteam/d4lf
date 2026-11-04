"""Pure item-rule evaluation over loaded rules and immutable settings."""

import logging
from typing import TYPE_CHECKING

from src.game_data import ItemRarity, ItemType, is_sigil
from src.item import MYTHICS_ALWAYS_KEPT_LABEL
from src.item.filter.equipment import FilterEquipmentMixin
from src.item.filter.matching import FilterMatchingMixin
from src.item.filter.rules import EvaluationSettings, LoadedRules
from src.item.filter.special import FilterSpecialMixin
from src.item.models import FilterResult, MatchedFilter

if TYPE_CHECKING:
    from src.item.models import Item

LOGGER = logging.getLogger(__name__)


class FilterEvaluator(FilterSpecialMixin, FilterEquipmentMixin, FilterMatchingMixin):
    """Evaluate one item against a complete rules and settings snapshot."""

    def __init__(self, rules: LoadedRules | None = None, evaluation_settings: EvaluationSettings | None = None) -> None:
        self._rules = rules or LoadedRules.empty()
        self.evaluation_settings = evaluation_settings or EvaluationSettings()

    @property
    def rules(self) -> LoadedRules:
        return self._rules

    @rules.setter
    def rules(self, value: LoadedRules) -> None:
        self._rules = value

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
            return self._check_seal_charm_filters(item, self.rules.seal_filters, "Seals", "Mythic Seal")
        if item.item_type == ItemType.Charm:
            return self._check_seal_charm_filters(item, self.rules.charm_filters, "Charms", "Mythic Charm")
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
            result = FilterResult(
                keep=True, matched=[MatchedFilter(profile=MYTHICS_ALWAYS_KEPT_LABEL, aspect_match=True)]
            )
        if not result.keep:
            return self._check_cosmetic(item)
        return result
