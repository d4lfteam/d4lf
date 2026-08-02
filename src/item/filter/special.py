import logging
from typing import TYPE_CHECKING

from src.game_data import ItemRarity, SigilRules
from src.item.models import FilterResult, MatchedFilter
from src.profiles import CharmFilterModel, SigilPriority
from src.settings import CosmeticFilterType, get_settings

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from src.item.filter.matching import FilterContext
    from src.item.models import Item
    from src.profiles import DynamicCharmFilterModel, DynamicSealFilterModel

LOGGER = logging.getLogger(__name__)


class FilterSpecialMixin:
    @staticmethod
    def _check_cosmetic(item: Item) -> FilterResult:
        res = FilterResult(keep=False, matched=[])
        if get_settings().general.handle_cosmetics == CosmeticFilterType.junk or (
            get_settings().general.handle_cosmetics == CosmeticFilterType.ignore and not item.cosmetic_upgrade
        ):
            return res
        if not item.cosmetic_upgrade:
            return res
        LOGGER.info(f"{item.original_name} -- Matched new cosmetic")
        res.keep = True
        res.matched.append(MatchedFilter("Cosmetics"))
        return res

    def _check_sigil(self: FilterContext, item: Item) -> FilterResult:
        res = FilterResult(keep=False, matched=[])
        sigil_item = SigilRules.default().for_item(item)
        if not self.sigil_filters.items():
            LOGGER.info(f"{item.original_name} -- Matched Sigils")
            res.keep = True
            res.matched.append(MatchedFilter("Sigils not filtered"))
        for profile_name, profile_filter in self.sigil_filters.items():
            blacklist_empty = not profile_filter.blacklist
            is_in_blacklist = any(sigil_item.matches(rule) for rule in profile_filter.blacklist)
            blacklist_ok = True if blacklist_empty else not is_in_blacklist
            whitelist_empty = not profile_filter.whitelist
            is_in_whitelist = any(sigil_item.matches(rule) for rule in profile_filter.whitelist)
            rarity_match = bool(profile_filter.rarities) and (
                sigil_item.rarity is not None and sigil_item.rarity in profile_filter.rarities
            )
            if profile_filter.rarities and not rarity_match and not is_in_whitelist:
                continue
            whitelist_ok = True if whitelist_empty else is_in_whitelist or rarity_match
            if (blacklist_empty and not whitelist_empty and not whitelist_ok) or (
                whitelist_empty and not blacklist_empty and not blacklist_ok
            ):
                continue
            if not blacklist_empty and not whitelist_empty:
                if not blacklist_ok and not whitelist_ok:
                    continue
                if is_in_blacklist and is_in_whitelist:
                    if profile_filter.priority == SigilPriority.whitelist and not whitelist_ok:
                        continue
                    if profile_filter.priority == SigilPriority.blacklist and not blacklist_ok:
                        continue
                elif (is_in_blacklist and not blacklist_ok) or (not is_in_whitelist and not whitelist_ok):
                    continue
            LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Sigils")
            res.keep = True
            res.matched.append(MatchedFilter(f"{profile_name}"))
        if sigil_item.rarity == ItemRarity.Mythic and not res.keep:
            LOGGER.info(f"{item.original_name} -- Matched mythic sigil, always kept")
            res.keep = True
            res.matched.append(MatchedFilter("Mythic Sigil"))
        return res

    def _check_seal_charm_filters(
        self: FilterContext,
        seal_or_charm: Item,
        seal_or_charm_filters: Mapping[str, Sequence[DynamicSealFilterModel | DynamicCharmFilterModel]],
        section_name: str,
        mythic_name: str,
    ) -> FilterResult:
        res = FilterResult(keep=False, matched=[])
        for profile_name, profile_filter in seal_or_charm_filters.items():
            for filter_item in profile_filter:
                filter_name = next(iter(filter_item.root.keys()))
                filter_spec = filter_item.root[filter_name]
                if filter_spec.rarities and seal_or_charm.rarity not in filter_spec.rarities:
                    continue
                if not self._match_greater_affix_count(filter_spec.min_greater_affix_count, seal_or_charm.affixes):
                    continue
                matched_affixes = []
                if filter_spec.affix_pool:
                    matched_affixes = self._match_affixes_count(
                        filter_spec.affix_pool, seal_or_charm.affixes, filter_spec.min_greater_affix_count
                    )
                    if not matched_affixes:
                        continue
                matched_aspect = False  # charms match either a set or unique aspect
                matched_set = False
                if not self._check_unique_aspects_for_item(seal_or_charm, filter_spec.unique_aspect):
                    continue
                if filter_spec.unique_aspect:
                    matched_aspect = True
                if isinstance(filter_spec, CharmFilterModel) and filter_spec.set:
                    if not seal_or_charm.set or seal_or_charm.set not in filter_spec.set:
                        continue
                    matched_set = True
                LOGGER.info(
                    f"{seal_or_charm.original_name} -- Matched {profile_name}.{section_name}.{filter_name}: "
                    f"{[affix.name for affix in matched_affixes]}"
                )
                if matched_aspect or matched_set:
                    LOGGER.info(
                        f"{seal_or_charm.original_name} -- Matched {profile_name}.{section_name}.{filter_name}: "
                        f"{'Unique aspect' if matched_aspect else 'Set'}"
                    )
                res.keep = True
                res.matched.append(
                    MatchedFilter(
                        f"{profile_name}.{section_name}.{filter_name}",
                        matched_affixes,
                        aspect_match=matched_aspect,
                        set_match=matched_set,
                    )
                )
        if not res.keep and seal_or_charm.rarity == ItemRarity.Mythic:
            LOGGER.info(f"{seal_or_charm.original_name} -- Matched mythic {section_name.lower()}, always kept")
            res.keep = True
            res.matched.append(MatchedFilter(mythic_name))
        return res

    def _check_tribute(self: FilterContext, item: Item) -> FilterResult:
        res = FilterResult(keep=False, matched=[])
        if not self.tribute_filters.items():
            LOGGER.info(f"{item.original_name} -- Matched Tributes")
            res.keep = True
            res.matched.append(MatchedFilter("Tributes not filtered"))
        for profile_name, filter_item in self.tribute_filters.items():
            name_match = (
                item.name is not None
                and bool(filter_item.name)
                and any(item.name.startswith(name) for name in filter_item.name)
            )
            rarity_match = bool(filter_item.rarities) and item.rarity in filter_item.rarities
            if not name_match and not rarity_match:
                continue
            LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Tributes")
            res.keep = True
            res.matched.append(MatchedFilter(f"{profile_name}"))
        if item.rarity == ItemRarity.Mythic and not res.keep:
            LOGGER.info(f"{item.original_name} -- Matched mythic tribute, always kept")
            res.keep = True
            res.matched.append(MatchedFilter("Mythic Tribute"))
        return res
