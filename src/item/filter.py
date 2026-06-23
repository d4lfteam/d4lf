import logging
import pathlib
import re
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import yaml
from pydantic import ValidationError
from yaml import MappingNode, MarkedYAMLError

from src.config.loader import IniConfigLoader
from src.config.profile_models import (
    AffixAspectFilterModel,
    AffixFilterCountModel,
    AffixFilterModel,
    DynamicItemFilterModel,
    GlobalUniqueModel,
    ParagonPayloadModel,
    ProfileModel,
    SigilConditionModel,
    SigilFilterModel,
    SigilPriority,
    TributeFilterModel,
)
from src.config.settings_models import AspectFilterType, CosmeticFilterType, UnfilteredUniquesType
from src.dataloader import Dataloader
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType, is_sigil
from src.item.data.rarity import ItemRarity
from src.scripts.common import ASPECT_UPGRADES_LABEL

if TYPE_CHECKING:
    from src.item.data.aspect import Aspect
    from src.item.models import Item

LOGGER = logging.getLogger(__name__)


@dataclass
class MatchedFilter:
    profile: str
    matched_affixes: list[Affix] = field(default_factory=list)
    aspect_match: bool = False


@dataclass
class FilterResult:
    keep: bool
    matched: list[MatchedFilter]


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
    paragon_filters: dict[str, ParagonPayloadModel] = {}
    global_unique_filters = {}
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
        res = FilterResult(keep=False, matched=[])
        if not self.affix_filters:
            return FilterResult(keep=False, matched=[])
        non_tempered_affixes = [affix for affix in item.affixes if affix.type != AffixType.tempered]
        for profile_name, profile_filter in self.affix_filters.items():
            for filter_item in profile_filter:
                filter_name = next(iter(filter_item.root.keys()))
                filter_spec = filter_item.root[filter_name]
                # check item type
                if not self._match_item_type(expected_item_types=filter_spec.item_type, item_type=item.item_type):
                    continue
                # check item rarity
                if filter_spec.rarities and item.rarity not in filter_spec.rarities:
                    continue
                # check item power
                if not self._match_item_power(min_power=filter_spec.min_power, item_power=item.power):
                    continue
                # check greater affixes
                if not self._match_greater_affix_count(
                    expected_min_count=filter_spec.min_greater_affix_count, item_affixes=non_tempered_affixes
                ):
                    continue
                # check the unique aspect. The model enforces name uniqueness so we can safely grab the first one that matches
                matched_unique_aspect = None
                for unique_aspect in filter_spec.unique_aspect:
                    if self._match_item_aspect_or_affix(expected_aspect=unique_aspect, item_aspect=item.aspect):
                        matched_unique_aspect = unique_aspect
                        break
                if filter_spec.unique_aspect and not matched_unique_aspect:
                    continue
                # If the item is unique but doesn't match a unique aspect we continue. We don't check affixes
                if item.rarity in [ItemRarity.Unique, ItemRarity.Mythic] and not matched_unique_aspect:
                    continue
                # check the aspect matches the min percent. We only check the one that passed the previous check
                if matched_unique_aspect and not self._match_item_roll_is_in_percent_range(
                    expected_percent=matched_unique_aspect.min_percent_of_aspect, item_aspect_or_affix=item.aspect
                ):
                    continue
                # check affixes
                matched_affixes = []
                if filter_spec.affix_pool:
                    matched_affixes = self._match_affixes_count(
                        expected_affixes=filter_spec.affix_pool,
                        item_affixes=non_tempered_affixes,
                        min_greater_affix_count=filter_spec.min_greater_affix_count,
                    )
                    if not matched_affixes:
                        continue
                # check inherent
                matched_inherents = []
                if filter_spec.inherent_pool:
                    matched_inherents = self._match_affixes_count(
                        expected_affixes=filter_spec.inherent_pool,
                        item_affixes=item.inherent,
                        min_greater_affix_count=filter_spec.min_greater_affix_count,
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
                if filter_spec.unique_aspect:
                    LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Affixes.{filter_name}: Unique aspect")
                res.keep = True
                res.matched.append(
                    MatchedFilter(f"{profile_name}.{filter_name}", all_matches, bool(filter_spec.unique_aspect))
                )
        return res

    def _check_legendary_aspect(self, item: Item) -> FilterResult:
        res = FilterResult(keep=False, matched=[])

        if item.codex_upgrade and self.aspect_upgrade_filters:
            # See if the item matches any legendary aspects that were in the profile
            for profile_name, profile_filter in self.aspect_upgrade_filters.items():
                if item.aspect and any(
                    legendary_aspect_name == item.aspect.name for legendary_aspect_name in profile_filter
                ):
                    LOGGER.info(f"{item.original_name} -- Matched build-specific aspects that updates codex")
                    res.keep = True
                    res.matched.append(MatchedFilter(f"{profile_name}.{ASPECT_UPGRADES_LABEL}", aspect_match=True))

            if res.keep:
                return res

        if IniConfigLoader().general.keep_aspects == AspectFilterType.none or (
            IniConfigLoader().general.keep_aspects == AspectFilterType.upgrade and not item.codex_upgrade
        ):
            return res
        LOGGER.info(f"{item.original_name} -- Matched Aspects that updates codex")
        res.keep = True
        res.matched.append(MatchedFilter(ASPECT_UPGRADES_LABEL, aspect_match=True))
        return res

    @staticmethod
    def _check_cosmetic(item: Item) -> FilterResult:
        res = FilterResult(keep=False, matched=[])
        if IniConfigLoader().general.handle_cosmetics == CosmeticFilterType.junk or (
            IniConfigLoader().general.handle_cosmetics == CosmeticFilterType.ignore and not item.cosmetic_upgrade
        ):
            return res
        if not item.cosmetic_upgrade:
            return res
        LOGGER.info(f"{item.original_name} -- Matched new cosmetic")
        res.keep = True
        res.matched.append(MatchedFilter("Cosmetics"))
        return res

    def _get_sigil_rarity(self, item: Item) -> ItemRarity | None:
        if item.rarity is not None:
            return item.rarity
        rarity_map = Dataloader().affix_sigil_dict_all["rarities"]
        sigil_affixes = item.affixes + item.inherent
        for affix in sigil_affixes:
            if affix.name in rarity_map:
                return ItemRarity(rarity_map[affix.name].lower())
        LOGGER.warning(f"Could not resolve sigil rarity from affixes: {[a.name for a in sigil_affixes]}")
        return None

    def _check_sigil(self, item: Item) -> FilterResult:
        res = FilterResult(keep=False, matched=[])
        if not self.sigil_filters.items():
            LOGGER.info(f"{item.original_name} -- Matched Sigils")
            res.keep = True
            res.matched.append(MatchedFilter("Sigils not filtered"))
        for profile_name, profile_filter in self.sigil_filters.items():
            if profile_filter.rarities:
                sigil_rarity = self._get_sigil_rarity(item)
                if sigil_rarity is None or sigil_rarity not in profile_filter.rarities:
                    continue  # fail-closed; warning logged in _get_sigil_rarity
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

        if item.rarity == ItemRarity.Mythic and not res.keep:
            LOGGER.info(f"{item.original_name} -- Matched mythic sigil, always kept")
            res.keep = True
            res.matched.append(MatchedFilter("Mythic Sigil"))
        return res

    def _check_tribute(self, item: Item) -> FilterResult:
        res = FilterResult(keep=False, matched=[])
        if not self.tribute_filters.items():
            LOGGER.info(f"{item.original_name} -- Matched Tributes")
            res.keep = True
            res.matched.append(MatchedFilter("Tributes not filtered"))

        for profile_name, profile_filter in self.tribute_filters.items():
            for filter_item in profile_filter:
                if filter_item.name and not item.name.startswith(filter_item.name):
                    continue

                if filter_item.rarities and item.rarity not in filter_item.rarities:
                    continue

                LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Tributes")
                res.keep = True
                res.matched.append(MatchedFilter(f"{profile_name}"))

        if item.rarity == ItemRarity.Mythic and not res.keep:
            LOGGER.info(f"{item.original_name} -- Matched mythic tribute, always kept")
            res.keep = True
            res.matched.append(MatchedFilter("Mythic Tribute"))
        return res

    def _check_global_unique_filter(self, item: Item) -> FilterResult:
        res = FilterResult(keep=False, matched=[])

        if not self.global_unique_filters:
            keep = IniConfigLoader().general.handle_uniques != UnfilteredUniquesType.junk
            return FilterResult(keep, [])
        for profile_name, profile_filter in self.global_unique_filters.items():
            for filter_item in profile_filter:
                # check item power
                if not self._match_item_power(min_power=filter_item.min_power, item_power=item.power):
                    continue
                # check greater affixes - Checks total item-level GAs
                if not self._match_greater_affix_count(
                    expected_min_count=filter_item.min_greater_affix_count, item_affixes=item.affixes
                ):
                    continue
                # check aspect is in percent range
                if not self._match_item_roll_is_in_percent_range(
                    expected_percent=filter_item.min_percent_of_aspect, item_aspect_or_affix=item.aspect
                ):
                    continue
                LOGGER.info(f"{item.original_name} -- Matched {profile_name}.GlobalUniques: {item.aspect.name}")
                res.keep = True
                matched_full_name = f"{profile_name}.{item.aspect.name}"
                if filter_item.profile_alias:
                    matched_full_name = f"{filter_item.profile_alias}.{item.aspect.name}"
                res.matched.append(MatchedFilter(matched_full_name, aspect_match=True))

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
            if not (count_group.min_count <= len(group_res) <= count_group.max_count):
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
    def _match_item_roll_is_in_percent_range(expected_percent: int, item_aspect_or_affix: Aspect | Affix) -> bool:
        if expected_percent == 0 or item_aspect_or_affix.max_value is None or item_aspect_or_affix.min_value is None:
            return True

        if item_aspect_or_affix.max_value == item_aspect_or_affix.min_value:
            return True

        if not Filter._is_smaller_roll_better(item_aspect_or_affix):
            percent_float = expected_percent / 100.0
            return (item_aspect_or_affix.value - item_aspect_or_affix.min_value) / (
                item_aspect_or_affix.max_value - item_aspect_or_affix.min_value
            ) >= percent_float

        # This is the case where a smaller number is better
        percent_float = (100 - expected_percent) / 100.0
        return (item_aspect_or_affix.value - item_aspect_or_affix.max_value) / (
            item_aspect_or_affix.min_value - item_aspect_or_affix.max_value
        ) <= percent_float

    @staticmethod
    def _is_smaller_roll_better(item_aspect_or_affix: Aspect | Affix) -> bool:
        return (
            item_aspect_or_affix.max_value is not None
            and item_aspect_or_affix.min_value is not None
            and item_aspect_or_affix.max_value < item_aspect_or_affix.min_value
        )

    @staticmethod
    def _match_item_value_threshold(expected_value: float, item_aspect_or_affix: Aspect | Affix) -> bool:
        if Filter._is_smaller_roll_better(item_aspect_or_affix):
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
        if item_aspect is None:
            return False
        if expected_aspect.name != item_aspect.name:
            return False

        if expected_aspect.value is not None:
            if item_aspect.value is None:
                # Chaos uniques and probably bloodied items have a fixed aspect number.
                # There is no reason to compare it, it is always at max
                return bool(is_fixed_aspect_value)
            if not self._match_item_value_threshold(expected_aspect.value, item_aspect):
                return False
        expected_affix_percent = getattr(expected_aspect, "min_percent_of_affix", 0)
        if expected_affix_percent:
            if isinstance(item_aspect, Affix) and item_aspect.type == AffixType.greater:
                return True
            if not self._match_item_roll_is_in_percent_range(
                expected_percent=expected_affix_percent, item_aspect_or_affix=item_aspect
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
        self.paragon_filters: dict[str, ParagonPayloadModel] = {}
        self.sigil_filters: dict[str, SigilFilterModel] = {}
        self.tribute_filters: dict[str, list[TributeFilterModel]] = {}
        self.global_unique_filters: dict[str, list[GlobalUniqueModel]] = {}
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
                except yaml.YAMLError as e:
                    LOGGER.error(f"Error in the YAML file {profile_path}: {e}")
                    continue
                if config is None:
                    LOGGER.error(f"Empty YAML file {profile_path}, please remove it")
                    continue

                info_str = f"Loading profile {profile_str}: "
                try:
                    data = ProfileModel(name=profile_str, **config)
                except ValidationError as e:
                    LOGGER.error(
                        f"There were errors validating the profile at {profile_path}. This most likely means it is an old profile and the code has changed since it was created. The easiest solution is to delete the profile and import it again, or edit it manually using the errors below to guide you. The profile is skipped."
                    )
                    profile_errors = re.sub(
                        r"For further information visit https://errors\.pydantic\.dev/\d+(\.\d+)+/v/value_error\s*",
                        "",
                        str(e),
                    )
                    LOGGER.error(f"Validation error in {profile_path}: {profile_errors}")
                    continue

                sections: list[str] = []
                if data.affixes:
                    self.affix_filters[data.name] = data.affixes
                    sections.append("Affixes")
                if data.aspect_upgrades:
                    self.aspect_upgrade_filters[data.name] = data.aspect_upgrades
                    sections.append(ASPECT_UPGRADES_LABEL)
                if data.sigils and (data.sigils.blacklist or data.sigils.whitelist or data.sigils.rarities):
                    self.sigil_filters[data.name] = data.sigils
                    sections.append("Sigils")
                if data.tributes:
                    self.tribute_filters[data.name] = data.tributes
                    sections.append("Tributes")
                if data.global_uniques:
                    self.global_unique_filters[data.name] = data.global_uniques
                    sections.append("GlobalUniques")
                if data.paragon:
                    self.paragon_filters[data.name] = data.paragon
                    sections.append("Paragon")

                info_str += " ".join(sections)
                LOGGER.info(info_str.rstrip())
            self.last_loaded = time.time()
            self.last_profile_list = IniConfigLoader().general.profiles.copy()

    def get_paragon_filters(self) -> dict[str, ParagonPayloadModel]:
        """Return the loaded Paragon payloads, reloading profiles when needed."""
        if not self.files_loaded or self._did_files_change():
            self.load_files()
        return self.paragon_filters

    def should_keep(self, item: Item) -> FilterResult:
        if not self.files_loaded or self._did_files_change():
            self.load_files()

        res = FilterResult(keep=False, matched=[])

        if is_sigil(item.item_type):
            return self._check_sigil(item)

        if item.item_type == ItemType.Tribute:
            return self._check_tribute(item)

        if item.item_type is None or item.power is None:
            return res

        keep_affixes = self._check_affixes(item)
        if keep_affixes.keep:
            return keep_affixes
        if item.rarity == ItemRarity.Legendary:
            res = self._check_legendary_aspect(item)
        elif item.rarity == ItemRarity.Unique:
            res = self._check_global_unique_filter(item)
        elif item.rarity == ItemRarity.Mythic:
            # We always keep mythics
            res = FilterResult(keep=True, matched=[MatchedFilter(profile="Mythics always kept", aspect_match=True)])

        # After checking all possible options, if we still don't match, we check for a cosmetic upgrade
        if not res.keep:
            return self._check_cosmetic(item)

        return res
