import logging
import os
import sys
import time
from dataclasses import dataclass, field

import yaml
from pydantic import ValidationError
from yaml import MappingNode, MarkedYAMLError

from src.config.loader import IniConfigLoader
from src.config.models import (
    AffixAspectFilterModel,
    AffixFilterCountModel,
    AffixFilterModel,
    AspectFilterType,
    ComparisonType,
    DynamicItemFilterModel,
    ProfileModel,
    SigilConditionModel,
    SigilFilterModel,
    SigilPriority,
    UnfilteredUniquesType,
    UniqueModel,
)
from src.item.data.affix import Affix, AffixType
from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.models import Item

LOGGER = logging.getLogger(__name__)


@dataclass
class MatchedFilter:
    profile: str
    matched_affixes: list[Affix] = field(default_factory=list)
    did_match_aspect: bool = False


@dataclass
class FilterResult:
    keep: bool
    matched: list[MatchedFilter]
    unique_aspect_in_profile = False
    all_unique_filters_are_aspects = False


class _UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node: MappingNode, deep=False):
        mapping = set()
        for key_node, _ in node.value:
            if ":merge" in key_node.tag:
                continue
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise MarkedYAMLError(problem=f"Duplicate {key!r} key found in YAML", problem_mark=key_node.start_mark)
            mapping.add(key)
        return super().construct_mapping(node, deep)


class Filter:
    affix_filters = {}
    aspect_filters = {}
    unique_filters = {}
    sigil_filters = {}

    files_loaded = False
    all_file_pathes = []
    last_loaded = None

    _initialized: bool = False
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _check_affixes(self, item: Item) -> FilterResult:
        res = FilterResult(False, [])
        if not self.affix_filters:
            return FilterResult(True, [])
        non_tempered_affixes = [affix for affix in item.affixes if affix.type != AffixType.tempered]
        for profile_name, profile_filter in self.affix_filters.items():
            for filter_item in profile_filter:
                filter_name = next(iter(filter_item.root.keys()))
                filter_spec = filter_item.root[filter_name]
                # check item type
                if not self._match_item_type(expected_item_types=filter_spec.itemType, item_type=item.item_type):
                    continue
                # check item power
                if not self._match_item_power(min_power=filter_spec.minPower, item_power=item.power):
                    continue
                # check greater affixes
                if not self._match_greater_affix_count(
                    expected_min_count=filter_spec.minGreaterAffixCount, item_affixes=non_tempered_affixes
                ):
                    continue
                # check affixes
                matched_affixes = []
                if filter_spec.affixPool:
                    matched_affixes = self._match_affixes_count(expected_affixes=filter_spec.affixPool, item_affixes=non_tempered_affixes)
                    if not matched_affixes:
                        continue
                # check inherent
                matched_inherents = []
                if filter_spec.inherentPool:
                    matched_inherents = self._match_affixes_count(expected_affixes=filter_spec.inherentPool, item_affixes=item.inherent)
                    if not matched_inherents:
                        continue
                all_matches = matched_affixes + matched_inherents
                LOGGER.info(f"Matched {profile_name}.Affixes.{filter_name}: {[x.name for x in all_matches]}")
                res.keep = True
                res.matched.append(MatchedFilter(f"{profile_name}.{filter_name}", all_matches))
        return res

    @staticmethod
    def _check_aspect(item: Item) -> FilterResult:
        res = FilterResult(False, [])
        if IniConfigLoader().general.keep_aspects == AspectFilterType.none or (
            IniConfigLoader().general.keep_aspects == AspectFilterType.upgrade and not item.codex_upgrade
        ):
            return res
        LOGGER.info("Matched Aspects that updates codex")
        res.keep = True
        res.matched.append(MatchedFilter("Aspects", did_match_aspect=True))
        return res

    def _check_sigil(self, item: Item) -> FilterResult:
        res = FilterResult(False, [])
        if not self.sigil_filters.items():
            LOGGER.info("Matched Sigils")
            res.keep = True
            res.matched.append(MatchedFilter("default"))
        for profile_name, profile_filter in self.sigil_filters.items():
            # check item power
            if not self._match_item_power(max_power=profile_filter.maxTier, min_power=profile_filter.minTier, item_power=item.power):
                continue

            blacklist_empty = not profile_filter.blacklist
            is_in_blacklist = self._match_affixes_sigils(
                expected_affixes=profile_filter.blacklist, sigil_affixes=item.affixes + item.inherent
            )
            blacklist_ok = True if blacklist_empty else not is_in_blacklist
            whitelist_empty = not profile_filter.whitelist
            is_in_whitelist = self._match_affixes_sigils(
                expected_affixes=profile_filter.whitelist, sigil_affixes=item.affixes + item.inherent
            )
            whitelist_ok = True if whitelist_empty else is_in_whitelist

            if blacklist_empty and not whitelist_empty and not whitelist_ok or whitelist_empty and not blacklist_empty and not blacklist_ok:
                continue
            if not blacklist_empty and not whitelist_empty:
                if not blacklist_ok and not whitelist_ok:
                    continue
                if is_in_blacklist and is_in_whitelist:
                    if profile_filter.priority == SigilPriority.whitelist and not whitelist_ok:
                        continue
                    if profile_filter.priority == SigilPriority.blacklist and not blacklist_ok:
                        continue
                elif is_in_blacklist and not blacklist_ok or not is_in_whitelist and not whitelist_ok:
                    continue
            LOGGER.info(f"Matched {profile_name}.Sigils")
            res.keep = True
            res.matched.append(MatchedFilter(f"{profile_name}"))
        return res

    def _check_unique_item(self, item: Item) -> FilterResult:
        res = FilterResult(False, [])
        all_filters_are_aspect = True
        if not self.unique_filters:
            keep = IniConfigLoader().general.handle_uniques != UnfilteredUniquesType.junk or item.rarity == ItemRarity.Mythic
            return FilterResult(keep, [])
        for profile_name, profile_filter in self.unique_filters.items():
            for filter_item in profile_filter:
                if not filter_item.aspect:
                    all_filters_are_aspect = False
                elif item.aspect and filter_item.aspect.name == item.aspect.name:
                    res.unique_aspect_in_profile = True
                # check mythic
                if filter_item.mythic and item.rarity != ItemRarity.Mythic:
                    continue
                # check item type
                if not self._match_item_type(expected_item_types=filter_item.itemType, item_type=item.item_type):
                    continue
                # check item power
                if not self._match_item_power(min_power=filter_item.minPower, item_power=item.power):
                    continue
                # check aspect
                if not self._match_item_aspect_or_affix(expected_aspect=filter_item.aspect, item_aspect=item.aspect):
                    continue
                # check affixes
                if not self._match_affixes_uniques(expected_affixes=filter_item.affix, item_affixes=item.affixes):
                    continue
                # check greater affixes
                if not self._match_greater_affix_count(expected_min_count=filter_item.minGreaterAffixCount, item_affixes=item.affixes):
                    continue
                LOGGER.info(f"Matched {profile_name}.Uniques: {item.aspect.name}")
                res.keep = True
                matched_full_name = f"{profile_name}.{item.aspect.name}"
                if filter_item.profileAlias:
                    matched_full_name = f"{filter_item.profileAlias}.{item.aspect.name}"
                res.matched.append(MatchedFilter(matched_full_name, did_match_aspect=True))
        res.all_unique_filters_are_aspects = all_filters_are_aspect

        # Always keep mythics no matter what
        # If all filters are for aspects specifically and none apply to this item, we default to handle_uniques config
        if not res.keep and (
            item.rarity == ItemRarity.Mythic
            or (
                res.all_unique_filters_are_aspects
                and not res.unique_aspect_in_profile
                and IniConfigLoader().general.handle_uniques != UnfilteredUniquesType.junk
            )
        ):
            res.keep = True

        return res

    def _did_files_change(self) -> bool:
        if self.last_loaded is None:
            return True
        return any(os.path.getmtime(file_path) > self.last_loaded for file_path in self.all_file_pathes)

    def _match_affixes_count(self, expected_affixes: list[AffixFilterCountModel], item_affixes: list[Affix]) -> list[Affix]:
        result = []
        for count_group in expected_affixes:
            greater_affix_count = 0
            group_res = []
            for affix in count_group.count:
                matched_item_affix = next((a for a in item_affixes if a.name == affix.name), None)
                if matched_item_affix is not None and self._match_item_aspect_or_affix(affix, matched_item_affix):
                    group_res.append(matched_item_affix)
                    if matched_item_affix.type == AffixType.greater:
                        greater_affix_count += 1
            if count_group.minCount <= len(group_res) <= count_group.maxCount and greater_affix_count >= count_group.minGreaterAffixCount:
                result.extend(group_res)
            else:  # if one group fails, everything fails
                return []
        return result

    @staticmethod
    def _match_affixes_sigils(expected_affixes: list[SigilConditionModel], sigil_affixes: list[Affix]) -> bool:
        for expected_affix in expected_affixes:
            if not [affix for affix in sigil_affixes if affix.name == expected_affix.name]:
                continue
            if expected_affix.condition and not any(affix.name in expected_affix.condition for affix in sigil_affixes):
                continue
            return True
        return False

    def _match_affixes_uniques(self, expected_affixes: list[AffixFilterModel], item_affixes: list[Affix]) -> bool:
        for expected_affix in expected_affixes:
            matched_item_affix = next((a for a in item_affixes if a.name == expected_affix.name), None)
            if matched_item_affix is None or not self._match_item_aspect_or_affix(expected_affix, matched_item_affix):
                return False
        return True

    def _match_greater_affix_count(self, expected_min_count: int, item_affixes: list[Affix]) -> bool:
        return expected_min_count <= len([x for x in item_affixes if x.type == AffixType.greater])

    @staticmethod
    def _match_item_aspect_or_affix(expected_aspect: AffixAspectFilterModel | None, item_aspect: Aspect | Affix) -> bool:
        if expected_aspect is None:
            return True
        if expected_aspect.name != item_aspect.name:
            return False
        if expected_aspect.value is not None:
            if item_aspect.value is None:
                return False
            if (expected_aspect.comparison == ComparisonType.larger and item_aspect.value < expected_aspect.value) or (
                expected_aspect.comparison == ComparisonType.smaller and item_aspect.value > expected_aspect.value
            ):
                return False
        return True

    @staticmethod
    def _match_item_power(min_power: int, item_power: int, max_power: int = sys.maxsize) -> bool:
        return min_power <= item_power <= max_power

    @staticmethod
    def _match_item_type(expected_item_types: list[ItemType], item_type: ItemType) -> bool:
        if not expected_item_types:
            return True
        return item_type in expected_item_types

    def load_files(self):
        self.files_loaded = True
        self.affix_filters: dict[str, list[DynamicItemFilterModel]] = {}
        self.sigil_filters: dict[str, SigilFilterModel] = {}
        self.unique_filters: dict[str, list[UniqueModel]] = {}
        profiles: list[str] = IniConfigLoader().general.profiles

        if not profiles:
            LOGGER.warning(
                "No profiles have been configured so no filtering will be done. If this is a mistake, use the profiles section of the config tab of gui.bat to activate the profiles you want to use."
            )
            return

        custom_profile_path = IniConfigLoader().user_dir / "profiles"
        self.all_file_pathes = []

        errors = False
        for profile_str in profiles:
            custom_file_path = custom_profile_path / f"{profile_str}.yaml"
            if custom_file_path.is_file():
                profile_path = custom_file_path
            else:
                LOGGER.error(f"Could not load profile {profile_str}. Checked: {custom_file_path}")
                continue

            self.all_file_pathes.append(profile_path)
            with open(profile_path, encoding="utf-8") as f:
                try:
                    config = yaml.load(stream=f, Loader=_UniqueKeyLoader)
                except Exception as e:
                    LOGGER.error(f"Error in the YAML file {profile_path}: {e}")
                    errors = True
                    continue
                if config is None:
                    LOGGER.error(f"Empty YAML file {profile_path}, please remove it")
                    continue

                info_str = f"Loading profile {profile_str}: "
                try:
                    data = ProfileModel(name=profile_str, **config)
                except ValidationError as e:
                    errors = True
                    LOGGER.error(f"Validation errors in {profile_path}")
                    LOGGER.error(e)
                    continue

                if data.Affixes:
                    self.affix_filters[data.name] = data.Affixes
                    info_str += "Affixes "
                if data.Sigils:
                    self.sigil_filters[data.name] = data.Sigils
                    info_str += "Sigils "
                if data.Uniques:
                    self.unique_filters[data.name] = data.Uniques
                    info_str += "Uniques"

                LOGGER.info(info_str)
        if errors:
            LOGGER.error("Errors occurred while loading profiles, please check the log for details")
            sys.exit(1)
        self.last_loaded = time.time()

    def should_keep(self, item: Item) -> FilterResult:
        if not self.files_loaded or self._did_files_change():
            self.load_files()

        res = FilterResult(False, [])

        if item.item_type is None or item.power is None:
            return res

        if item.item_type == ItemType.Sigil:
            return self._check_sigil(item)

        if item.rarity in [ItemRarity.Unique, ItemRarity.Mythic]:
            return self._check_unique_item(item)

        if item.rarity not in [ItemRarity.Unique, ItemRarity.Mythic]:
            keep_affixes = self._check_affixes(item)
            if keep_affixes.keep:
                return keep_affixes
            if item.rarity == ItemRarity.Legendary:
                return self._check_aspect(item)

        return res
