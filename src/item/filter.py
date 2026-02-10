import logging
import pathlib
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

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
    CosmeticFilterType,
    DynamicItemFilterModel,
    ProfileModel,
    SigilConditionModel,
    SigilFilterModel,
    SigilPriority,
    TributeFilterModel,
    UnfilteredUniquesType,
    UniqueModel,
)
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType, is_sigil
from src.item.data.rarity import ItemRarity
from src.scripts.common import ASPECT_UPGRADES_LABEL, is_junk_rarity

if TYPE_CHECKING:
    from src.item.data.aspect import Aspect
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
    aspect_upgrade_filters = {}
    unique_filters = {}
    sigil_filters = {}
    tribute_filters = {}

    files_loaded = False
    all_file_paths = []
    last_loaded = None
    last_profile_list = None

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
                    matched_affixes = self._match_affixes_count(
                        expected_affixes=filter_spec.affixPool,
                        item_affixes=non_tempered_affixes,
                        min_greater_affix_count=filter_spec.minGreaterAffixCount,
                    )
                    if not matched_affixes:
                        continue
                # check inherent
                matched_inherents = []
                if filter_spec.inherentPool:
                    matched_inherents = self._match_affixes_count(
                        expected_affixes=filter_spec.inherentPool,
                        item_affixes=item.inherent,
                        min_greater_affix_count=filter_spec.minGreaterAffixCount,
                    )
                    if not matched_inherents:
                        continue
                all_matches = matched_affixes + matched_inherents
                # Build a detailed string showing which affixes are GAs
                match_details = []
                for affix in all_matches:
                    if affix.type == AffixType.greater:
                        match_details.append(f"{affix.name} (GA)")
                    else:
                        match_details.append(affix.name)
                LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Affixes.{filter_name}: {match_details}")
                res.keep = True
                res.matched.append(MatchedFilter(f"{profile_name}.{filter_name}", all_matches))
        return res

    def _check_legendary_aspect(self, item: Item) -> FilterResult:
        res = FilterResult(False, [])

        if item.codex_upgrade and self.aspect_upgrade_filters:
            # See if the item matches any legendary aspects that were in the profile
            for profile_name, profile_filter in self.aspect_upgrade_filters.items():
                if item.aspect and any(
                    legendary_aspect_name == item.aspect.name for legendary_aspect_name in profile_filter
                ):
                    LOGGER.info(f"{item.original_name} -- Matched build-specific aspects that updates codex")
                    res.keep = True
                    res.matched.append(MatchedFilter(f"{profile_name}.{ASPECT_UPGRADES_LABEL}", did_match_aspect=True))

            if res.keep:
                return res

        if IniConfigLoader().general.keep_aspects == AspectFilterType.none or (
            IniConfigLoader().general.keep_aspects == AspectFilterType.upgrade and not item.codex_upgrade
        ):
            return res
        LOGGER.info(f"{item.original_name} -- Matched Aspects that updates codex")
        res.keep = True
        res.matched.append(MatchedFilter(ASPECT_UPGRADES_LABEL, did_match_aspect=True))
        return res

    @staticmethod
    def _check_cosmetic(item: Item) -> FilterResult:
        res = FilterResult(False, [])
        if IniConfigLoader().general.handle_cosmetics == CosmeticFilterType.junk or (
            IniConfigLoader().general.handle_cosmetics == CosmeticFilterType.ignore and not item.cosmetic_upgrade
        ):
            return res
        LOGGER.info(f"{item.original_name} -- Matched new cosmetic")
        res.keep = True
        res.matched.append(MatchedFilter("Cosmetics"))
        return res

    def _check_sigil(self, item: Item) -> FilterResult:
        res = FilterResult(False, [])
        if not self.sigil_filters.items():
            LOGGER.info(f"{item.original_name} -- Matched Sigils")
            res.keep = True
            res.matched.append(MatchedFilter("Sigils not filtered"))
        for profile_name, profile_filter in self.sigil_filters.items():
            blacklist_empty = not profile_filter.blacklist
            is_in_blacklist = self._match_affixes_sigils(
                expected_affixes=profile_filter.blacklist,
                sigil_name=item.name,
                sigil_affixes=item.affixes + item.inherent,
            )
            blacklist_ok = True if blacklist_empty else not is_in_blacklist
            whitelist_empty = not profile_filter.whitelist
            is_in_whitelist = self._match_affixes_sigils(
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
                    if profile_filter.priority == SigilPriority.whitelist and not whitelist_ok:
                        continue
                    if profile_filter.priority == SigilPriority.blacklist and not blacklist_ok:
                        continue
                elif (is_in_blacklist and not blacklist_ok) or (not is_in_whitelist and not whitelist_ok):
                    continue
            LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Sigils")
            res.keep = True
            res.matched.append(MatchedFilter(f"{profile_name}"))
        return res

    def _check_tribute(self, item: Item) -> FilterResult:
        res = FilterResult(False, [])
        if not self.tribute_filters.items():
            LOGGER.info(f"{item.original_name} -- Matched Tributes")
            res.keep = True
            res.matched.append(MatchedFilter("Tributes not filtered"))

        if item.rarity == ItemRarity.Mythic:
            LOGGER.info(f"{item.original_name} -- Matched mythic tribute, always kept")
            res.keep = True
            res.matched.append(MatchedFilter("Mythic Tribute"))

        for profile_name, profile_filter in self.tribute_filters.items():
            for filter_item in profile_filter:
                if filter_item.name and not item.name.startswith(filter_item.name):
                    continue

                if filter_item.rarities and item.rarity not in filter_item.rarities:
                    continue

                LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Tributes")
                res.keep = True
                res.matched.append(MatchedFilter(f"{profile_name}"))
        return res

    def _check_unique_item(self, item: Item) -> FilterResult:
        res = FilterResult(False, [])
        all_filters_are_aspect = True
        if not self.unique_filters:
            keep = (
                IniConfigLoader().general.handle_uniques != UnfilteredUniquesType.junk
                or item.rarity == ItemRarity.Mythic
            )
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
                if not self._match_item_aspect_or_affix(
                    expected_aspect=filter_item.aspect, item_aspect=item.aspect, is_chaos=item.is_chaos
                ):
                    continue
                # check affixes
                if not self._match_affixes_uniques(
                    expected_affixes=filter_item.affix,
                    item_affixes=item.affixes,
                    min_greater_affix_count=filter_item.minGreaterAffixCount,
                ):
                    continue

                # check greater affixes - Checks total item-level GAs
                if not self._match_greater_affix_count(
                    expected_min_count=filter_item.minGreaterAffixCount, item_affixes=item.affixes
                ):
                    continue
                # check aspect is in percent range
                if not self._match_aspect_is_in_percent_range(
                    expected_percent=filter_item.minPercentOfAspect, item_aspect=item.aspect
                ):
                    continue
                LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Uniques: {item.aspect.name}")
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

        # Force reload config from disk to get latest profile list
        IniConfigLoader().load()

        # Check if profile list changed (filter out empty strings)
        current_profiles = [p.strip() for p in IniConfigLoader().general.profiles if p.strip()]
        if self.last_profile_list != current_profiles:
            LOGGER.info(f"Profile list changed: {self.last_profile_list} → {current_profiles}")
            return True

        # Check if any profile files were modified
        return any(pathlib.Path(file_path).stat().st_mtime > self.last_loaded for file_path in self.all_file_paths)

    def _match_affixes_count(
        self, expected_affixes: list[AffixFilterCountModel], item_affixes: list[Affix], min_greater_affix_count: int = 0
    ) -> list[Affix]:
        result = []
        for count_group in expected_affixes:
            group_res = []

            # Do the normal affix matching first
            for affix in count_group.count:
                matched_item_affix = next((a for a in item_affixes if a.name == affix.name), None)
                if matched_item_affix is not None and self._match_item_aspect_or_affix(affix, matched_item_affix):
                    group_res.append(matched_item_affix)

            # Check minCount and maxCount
            if not (count_group.minCount <= len(group_res) <= count_group.maxCount):
                return []  # if one group fails, everything fails

            # Check want_greater requirements (2-mode system)
            want_greater_affixes = [a for a in count_group.count if getattr(a, "want_greater", False)]
            want_greater_count = len(want_greater_affixes)

            if want_greater_count > 0 and min_greater_affix_count > 0:
                if min_greater_affix_count > want_greater_count:
                    # Mode 1: ALL flagged affixes MUST be GA (hard requirement)
                    for affix in want_greater_affixes:
                        matched_item_affix = next((a for a in item_affixes if a.name == affix.name), None)
                        if matched_item_affix is None or matched_item_affix.type != AffixType.greater:
                            return []  # Flagged affix is missing or not GA, fail
                else:
                    # Mode 2: At least min_greater_affix_count of the flagged affixes must be GA (flexible)
                    flagged_ga_count = sum(
                        1
                        for affix in want_greater_affixes
                        if (matched := next((a for a in item_affixes if a.name == affix.name), None))
                        and matched.type == AffixType.greater
                    )
                    if flagged_ga_count < min_greater_affix_count:
                        return []  # Not enough flagged affixes are GA

            result.extend(group_res)
        return result

    @staticmethod
    def _match_affixes_sigils(
        expected_affixes: list[SigilConditionModel], sigil_name: str, sigil_affixes: list[Affix]
    ) -> bool:
        for expected_affix in expected_affixes:
            if sigil_name != expected_affix.name and not [
                affix for affix in sigil_affixes if affix.name == expected_affix.name
            ]:
                continue
            if expected_affix.condition and not any(affix.name in expected_affix.condition for affix in sigil_affixes):
                continue
            return True
        return False

    def _match_affixes_uniques(
        self, expected_affixes: list[AffixFilterModel], item_affixes: list[Affix], min_greater_affix_count: int = 0
    ) -> bool:
        # First, check if all expected affixes are present with correct values
        for expected_affix in expected_affixes:
            matched_item_affix = next((a for a in item_affixes if a.name == expected_affix.name), None)
            if matched_item_affix is None or not self._match_item_aspect_or_affix(expected_affix, matched_item_affix):
                return False

        # Then, check want_greater requirements (2-mode system)
        want_greater_affixes = [a for a in expected_affixes if getattr(a, "want_greater", False)]
        want_greater_count = len(want_greater_affixes)

        if want_greater_count > 0 and min_greater_affix_count > 0:
            if min_greater_affix_count > want_greater_count:
                # Mode 1: ALL flagged affixes MUST be GA (hard requirement)
                for affix in want_greater_affixes:
                    matched_item_affix = next((a for a in item_affixes if a.name == affix.name), None)
                    if matched_item_affix is None or matched_item_affix.type != AffixType.greater:
                        return False  # Flagged affix is missing or not GA
            else:
                # Mode 2: At least min_greater_affix_count of the flagged affixes must be GA (flexible)
                flagged_ga_count = sum(
                    1
                    for affix in want_greater_affixes
                    if (matched := next((a for a in item_affixes if a.name == affix.name), None))
                    and matched.type == AffixType.greater
                )
                if flagged_ga_count < min_greater_affix_count:
                    return False  # Not enough flagged affixes are GA

        return True

    @staticmethod
    def _match_greater_affix_count(expected_min_count: int, item_affixes: list[Affix]) -> bool:
        return expected_min_count <= len([x for x in item_affixes if x.type == AffixType.greater])

    @staticmethod
    def _match_aspect_is_in_percent_range(expected_percent: int, item_aspect: Aspect) -> bool:
        if expected_percent == 0 or item_aspect.max_value is None or item_aspect.min_value is None:
            return True

        if item_aspect.max_value > item_aspect.min_value:
            percent_float = expected_percent / 100.0
            return (item_aspect.value - item_aspect.min_value) / (
                item_aspect.max_value - item_aspect.min_value
            ) >= percent_float

        # This is the case where a smaller number is better
        percent_float = (100 - expected_percent) / 100.0
        return (item_aspect.value - item_aspect.max_value) / (
            item_aspect.min_value - item_aspect.max_value
        ) <= percent_float

    @staticmethod
    def _match_item_aspect_or_affix(
        expected_aspect: AffixAspectFilterModel | None, item_aspect: Aspect | Affix, is_chaos: bool = False
    ) -> bool:
        if expected_aspect is None:
            return True
        if expected_aspect.name != item_aspect.name:
            return False

        if expected_aspect.value is not None:
            if item_aspect.value is None:
                # Chaos uniques have a fixed aspect number. There is no reason to compare it, it is always at max
                return bool(is_chaos)
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
        self.aspect_upgrade_filters: dict[str, list[str]] = {}
        self.sigil_filters: dict[str, SigilFilterModel] = {}
        self.tribute_filters: dict[str, list[TributeFilterModel]] = {}
        self.unique_filters: dict[str, list[UniqueModel]] = {}
        profiles: list[str] = IniConfigLoader().general.profiles

        # Filter out empty strings
        profiles = [p.strip() for p in profiles if p.strip()]

        if not profiles:
            LOGGER.warning(
                "No profiles are currently loaded. Please load a profile via the Importer, Settings, or Edit Profile sections to begin using the tool."
            )
            self.last_loaded = time.time()
            self.last_profile_list = []
            return

        custom_profile_path = IniConfigLoader().user_dir / "profiles"
        self.all_file_paths = []

        errors = False
        for profile_str in profiles:
            custom_file_path = custom_profile_path / f"{profile_str}.yaml"
            if custom_file_path.is_file():
                profile_path = custom_file_path
            else:
                LOGGER.error(f"Could not load profile {profile_str}. Checked: {custom_file_path}")
                continue

            self.all_file_paths.append(profile_path)
            with pathlib.Path(profile_path).open(encoding="utf-8") as f:
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

                    if "minGreaterAffixCount" in str(e):
                        LOGGER.error("[CLEAN]%s", "=" * 80)
                        LOGGER.error("[CLEAN]%s", f"PROFILE VALIDATION FAILED: {profile_path}")
                        LOGGER.error("[CLEAN]%s", "=" * 80)
                        LOGGER.error("[CLEAN]")
                        LOGGER.error(
                            "[CLEAN]%s", "You are using an old, outdated field that must be removed from your profile."
                        )
                        LOGGER.error("[CLEAN]")
                        LOGGER.error("[CLEAN]%s", "WRONG (old way - pool level):")
                        LOGGER.error("[CLEAN]%s", "- Ring:")
                        LOGGER.error("[CLEAN]%s", "    itemType: [ring]")
                        LOGGER.error("[CLEAN]%s", "    minPower: 100")
                        LOGGER.error("[CLEAN]%s", "    affixPool:")
                        LOGGER.error("[CLEAN]%s", "    - count:")
                        LOGGER.error("[CLEAN]%s", "      - {name: strength}")
                        LOGGER.error("[CLEAN]%s", "      minCount: 2")
                        LOGGER.error("[CLEAN]%s", "      minGreaterAffixCount: 1  ← DELETE THIS LINE")
                        LOGGER.error("[CLEAN]")
                        LOGGER.error("[CLEAN]%s", "CORRECT (new way - item level):")
                        LOGGER.error("[CLEAN]%s", "- Ring:")
                        LOGGER.error("[CLEAN]%s", "    itemType: [ring]")
                        LOGGER.error("[CLEAN]%s", "    minPower: 100")
                        LOGGER.error("[CLEAN]%s", "    minGreaterAffixCount: 1  ← PUT IT HERE INSTEAD")
                        LOGGER.error("[CLEAN]%s", "    affixPool:")
                        LOGGER.error("[CLEAN]%s", "    - count:")
                        LOGGER.error("[CLEAN]%s", "      - {name: strength}")
                        LOGGER.error("[CLEAN]%s", "      minCount: 2")
                        LOGGER.error("[CLEAN]%s", "      # NO minGreaterAffixCount here anymore!")
                        LOGGER.error("[CLEAN]")
                        LOGGER.error("[CLEAN]%s", "=" * 80)
                        LOGGER.error(
                            "[CLEAN]%s", f"ACTION REQUIRED: Please make the above adjustments in: {profile_path}"
                        )
                        LOGGER.error("[CLEAN]%s", "=" * 80)
                    else:
                        LOGGER.error(f"Validation error in {profile_path}: {e}")

                    continue

                sections: list[str] = []
                if data.Affixes:
                    self.affix_filters[data.name] = data.Affixes
                    sections.append("Affixes")
                if data.AspectUpgrades:
                    self.aspect_upgrade_filters[data.name] = data.AspectUpgrades
                    sections.append(ASPECT_UPGRADES_LABEL)
                if data.Sigils and (data.Sigils.blacklist or data.Sigils.whitelist):
                    self.sigil_filters[data.name] = data.Sigils
                    sections.append("Sigils")
                if data.Tributes:
                    self.tribute_filters[data.name] = data.Tributes
                    sections.append("Tributes")
                if data.Uniques:
                    self.unique_filters[data.name] = data.Uniques
                    sections.append("Uniques")
                if data.Paragon:
                    sections.append("Paragon")

                info_str += " ".join(sections)
                LOGGER.info(info_str.rstrip())
            if errors:
                fatal_msg = "\n" + "\n".join(["=" * 80, "❌ FATAL: Cannot continue with invalid profiles", "=" * 80])
                LOGGER.error(fatal_msg)
                sys.exit(1)
            self.last_loaded = time.time()
            self.last_profile_list = IniConfigLoader().general.profiles.copy()

    def should_keep(self, item: Item) -> FilterResult:
        if not self.files_loaded or self._did_files_change():
            self.load_files()

        res = FilterResult(False, [])

        if is_sigil(item.item_type):
            return self._check_sigil(item)

        if item.item_type == ItemType.Tribute:
            return self._check_tribute(item)

        if item.item_type is None or item.power is None or (is_junk_rarity(item.rarity) and not item.cosmetic_upgrade):
            return res

        if item.rarity in [ItemRarity.Unique, ItemRarity.Mythic]:
            res = self._check_unique_item(item)
        else:
            keep_affixes = self._check_affixes(item)
            if keep_affixes.keep:
                return keep_affixes
            if item.rarity == ItemRarity.Legendary:
                res = self._check_legendary_aspect(item)

        # After checking all possible options, if we still don't match, we check for a cosmetic upgrade
        if not res.keep:
            return self._check_cosmetic(item)

        return res
