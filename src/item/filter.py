import logging
import operator
import pathlib
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.config.loader import IniConfigLoader
from src.config.profile_document import ProfileDocumentError, ProfileDocumentStore
from src.config.profile_models import (
    AffixAspectFilterModel,
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    CharmFilterModel,
    DynamicCharmFilterModel,
    DynamicItemFilterModel,
    DynamicSealFilterModel,
    GlobalUniqueModel,
    ParagonPayloadModel,
    SigilFilterModel,
    SigilPriority,
    TributeFilterModel,
)
from src.config.settings_models import AspectFilterType, CosmeticFilterType, UnfilteredUniquesType
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType, is_sigil
from src.item.data.rarity import ItemRarity
from src.item.sigil_rules import SigilRules
from src.scripts.common import ASPECT_UPGRADES_LABEL

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from src.item.data.aspect import Aspect
    from src.item.models import Item

LOGGER = logging.getLogger(__name__)


@dataclass
class MatchedFilter:
    profile: str
    matched_affixes: list[Affix] = field(default_factory=list)
    aspect_match: bool = False
    set_match: bool = False


@dataclass
class FilterResult:
    keep: bool
    matched: list[MatchedFilter]


class Filter:
    affix_filters: dict[str, list[DynamicItemFilterModel]] = {}
    aspect_upgrade_filters: dict[str, list[str]] = {}
    paragon_filters: dict[str, ParagonPayloadModel] = {}
    global_unique_filters: dict[str, list[GlobalUniqueModel]] = {}
    seal_filters: dict[str, list[DynamicSealFilterModel]] = {}
    charm_filters: dict[str, list[DynamicCharmFilterModel]] = {}
    sigil_filters: dict[str, SigilFilterModel] = {}
    tribute_filters: dict[str, TributeFilterModel] = {}

    files_loaded: bool = False
    all_file_paths: list[pathlib.Path] = []
    last_loaded: float | None = None
    last_profile_list: list[str] | None = None

    _initialized: bool = False
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _check_unique_aspects_for_item(self, item: Item, unique_aspects: list[AspectUniqueFilterModel]) -> bool:
        # check the unique aspect. The model enforces name uniqueness so we can safely grab the first one that matches
        matched_unique_aspect = None
        for unique_aspect in unique_aspects:
            if self._match_item_aspect_or_affix(expected_aspect=unique_aspect, item_aspect=item.aspect):
                matched_unique_aspect = unique_aspect
                break
        if unique_aspects and not matched_unique_aspect:
            return False
        # If the item is unique but doesn't match a unique aspect we continue. We don't check affixes
        if item.rarity in [ItemRarity.Unique, ItemRarity.Mythic] and not matched_unique_aspect:
            return False
        # check the aspect matches the min percent. We only check the one that passed the previous check
        if matched_unique_aspect is None:
            return True
        if item.aspect is None:
            return False
        return self._match_item_roll_is_in_percent_range(
            expected_percent=matched_unique_aspect.min_percent_of_aspect, item_aspect_or_affix=item.aspect
        )

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
                if not self._check_unique_aspects_for_item(item, filter_spec.unique_aspect):
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

    def _check_aspect_upgrades(self, item: Item) -> FilterResult:
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

    def _check_sigil(self, item: Item) -> FilterResult:
        res = FilterResult(keep=False, matched=[])
        sigil_item = SigilRules.default().for_item(item)
        if not self.sigil_filters.items():
            LOGGER.info(f"{item.original_name} -- Matched Sigils")
            res.keep = True
            res.matched.append(MatchedFilter("Sigils not filtered"))
        for profile_name, profile_filter in self.sigil_filters.items():
            if profile_filter.rarities and (
                sigil_item.rarity is None or sigil_item.rarity not in profile_filter.rarities
            ):
                continue  # fail-closed; unknown rarity is logged in SigilRules
            blacklist_empty = not profile_filter.blacklist
            is_in_blacklist = any(sigil_item.matches(rule) for rule in profile_filter.blacklist)
            blacklist_ok = True if blacklist_empty else not is_in_blacklist
            whitelist_empty = not profile_filter.whitelist
            is_in_whitelist = any(sigil_item.matches(rule) for rule in profile_filter.whitelist)
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

        if sigil_item.rarity == ItemRarity.Mythic and not res.keep:
            LOGGER.info(f"{item.original_name} -- Matched mythic sigil, always kept")
            res.keep = True
            res.matched.append(MatchedFilter("Mythic Sigil"))
        return res

    def _check_seal_charm_filters(
        self,
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

                if not self._match_greater_affix_count(
                    expected_min_count=filter_spec.min_greater_affix_count, item_affixes=seal_or_charm.affixes
                ):
                    continue

                matched_affixes = []
                if filter_spec.affix_pool:
                    matched_affixes = self._match_affixes_count(
                        expected_affixes=filter_spec.affix_pool,
                        item_affixes=seal_or_charm.affixes,
                        min_greater_affix_count=filter_spec.min_greater_affix_count,
                    )
                    if not matched_affixes:
                        continue

                # For charms we check the set or aspect
                matched_aspect = False
                matched_set = False

                if not self._check_unique_aspects_for_item(seal_or_charm, filter_spec.unique_aspect):
                    continue
                if filter_spec.unique_aspect:
                    matched_aspect = True

                if isinstance(filter_spec, CharmFilterModel) and filter_spec.set:
                    # You can't have both a unique aspect and a set
                    if not seal_or_charm.set:  # This would mean there's no set but a set is expected
                        continue
                    if seal_or_charm.set not in filter_spec.set:
                        continue
                    matched_set = True

                LOGGER.info(
                    f"{seal_or_charm.original_name} -- Matched {profile_name}.{section_name}.{filter_name}: {[affix.name for affix in matched_affixes]}"
                )
                if matched_aspect or matched_set:
                    LOGGER.info(
                        f"{seal_or_charm.original_name} -- Matched {profile_name}.{section_name}.{filter_name}: {'Unique aspect' if matched_aspect else 'Set'}"
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

    def _check_tribute(self, item: Item) -> FilterResult:
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

    def _check_global_unique_filter(self, item: Item) -> FilterResult:
        res = FilterResult(keep=False, matched=[])

        if not self.global_unique_filters:
            keep = IniConfigLoader().general.handle_uniques != UnfilteredUniquesType.junk
            return FilterResult(keep, [])
        for profile_name, profile_filter in self.global_unique_filters.items():
            for filter_item in profile_filter:
                if item.aspect is None:
                    continue
                item_aspect = item.aspect
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
                    expected_percent=filter_item.min_percent_of_aspect, item_aspect_or_affix=item_aspect
                ):
                    continue
                LOGGER.info(f"{item.original_name} -- Matched {profile_name}.GlobalUniques: {item_aspect.name}")
                res.keep = True
                matched_full_name = f"{profile_name}.{item_aspect.name}"
                if filter_item.profile_alias:
                    matched_full_name = f"{filter_item.profile_alias}.{item_aspect.name}"
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
            group_res = self._match_affix_group(
                count_group=count_group, item_affixes=item_affixes, min_greater_affix_count=min_greater_affix_count
            )
            if group_res is None:
                return []  # if one group fails, everything fails
            result.extend(group_res)
        return result

    def _match_affix_group(
        self, count_group: AffixFilterCountModel, item_affixes: list[Affix], min_greater_affix_count: int
    ) -> list[Affix] | None:
        expected_affixes = count_group.count
        compatible_item_indices = [
            [
                item_index
                for item_index, item_affix in enumerate(item_affixes)
                if self._match_item_aspect_or_affix(expected_affix, item_affix)
            ]
            for expected_affix in expected_affixes
        ]
        expected_order = sorted(
            range(len(expected_affixes)), key=lambda expected_index: len(compatible_item_indices[expected_index])
        )
        want_greater_indices = {
            expected_index
            for expected_index, expected_affix in enumerate(expected_affixes)
            if expected_affix.want_greater
        }
        required_greater_count = min(min_greater_affix_count, len(want_greater_indices))
        max_match_count = -1
        valid_assignment: list[tuple[int, int]] | None = None

        def visit(position: int, used_item_indices: set[int], assignment: list[tuple[int, int]]) -> None:
            nonlocal max_match_count, valid_assignment
            if position == len(expected_order):
                match_count = len(assignment)
                flagged_ga_count = sum(
                    1
                    for expected_index, item_index in assignment
                    if expected_index in want_greater_indices and item_affixes[item_index].type == AffixType.greater
                )
                meets_greater_requirement = flagged_ga_count >= required_greater_count
                if match_count > max_match_count:
                    max_match_count = match_count
                    valid_assignment = assignment.copy() if meets_greater_requirement else None
                elif match_count == max_match_count and meets_greater_requirement and valid_assignment is None:
                    valid_assignment = assignment.copy()
                return

            expected_index = expected_order[position]
            for item_index in compatible_item_indices[expected_index]:
                if item_index in used_item_indices:
                    continue
                used_item_indices.add(item_index)
                assignment.append((expected_index, item_index))
                visit(position + 1, used_item_indices, assignment)
                assignment.pop()
                used_item_indices.remove(item_index)
            visit(position + 1, used_item_indices, assignment)

        visit(0, set(), [])
        if valid_assignment is None or not (count_group.min_count <= max_match_count <= count_group.max_count):
            return None

        return [item_affixes[item_index] for _, item_index in sorted(valid_assignment, key=operator.itemgetter(0))]

    def _match_affixes_uniques(
        self, expected_affixes: list[AffixFilterModel], item_affixes: list[Affix], min_greater_affix_count: int = 0
    ) -> bool:
        if not expected_affixes:
            return True
        count_group = AffixFilterCountModel(
            count=expected_affixes, min_count=len(expected_affixes), max_count=len(expected_affixes)
        )
        return (
            self._match_affix_group(
                count_group=count_group, item_affixes=item_affixes, min_greater_affix_count=min_greater_affix_count
            )
            is not None
        )

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

        if not Filter._is_smaller_roll_better(item_aspect_or_affix):
            percent_float = expected_percent / 100.0
            return (value - min_value) / (max_value - min_value) >= percent_float

        # This is the case where a smaller number is better
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
    def _match_item_power(min_power: int, item_power: int | None, max_power: int = sys.maxsize) -> bool:
        if item_power is None:
            return False
        return min_power <= item_power <= max_power

    @staticmethod
    def _match_item_type(expected_item_types: list[ItemType], item_type: ItemType | None) -> bool:
        if not expected_item_types:
            return True
        return item_type in expected_item_types

    def load_files(self):
        self.files_loaded = True
        self.affix_filters: dict[str, list[DynamicItemFilterModel]] = {}
        self.aspect_upgrade_filters: dict[str, list[str]] = {}

        self.paragon_filters: dict[str, ParagonPayloadModel] = {}
        self.seal_filters: dict[str, list[DynamicSealFilterModel]] = {}
        self.charm_filters: dict[str, list[DynamicCharmFilterModel]] = {}
        self.sigil_filters: dict[str, SigilFilterModel] = {}
        self.tribute_filters: dict[str, TributeFilterModel] = {}
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
            try:
                data = ProfileDocumentStore.default().load(profile_path).profile
            except ProfileDocumentError as e:
                LOGGER.error(str(e))
                continue

            info_str = f"Loading profile {profile_str}: "
            sections: list[str] = []
            if data.affixes:
                self.affix_filters[data.name] = data.affixes
                sections.append("Affixes")
            if data.aspect_upgrades:
                self.aspect_upgrade_filters[data.name] = data.aspect_upgrades
                sections.append(ASPECT_UPGRADES_LABEL)
            if data.seals:
                self.seal_filters[data.name] = data.seals
                sections.append("Seals")
            if data.charms:
                self.charm_filters[data.name] = data.charms
                sections.append("Charms")
            if data.sigils and (data.sigils.blacklist or data.sigils.whitelist or data.sigils.rarities):
                self.sigil_filters[data.name] = data.sigils
                sections.append("Sigils")
            if data.tributes is not None:
                self.tribute_filters[data.name] = data.tributes
                sections.append("Tributes")
            if data.global_uniques:
                self.global_unique_filters[data.name] = data.global_uniques
                sections.append("GlobalUniques")
            if data.paragon:
                self.paragon_filters[profile_path.stem] = data.paragon
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

        if item.item_type == ItemType.HoradricSeal:
            return self._check_seal_charm_filters(
                seal_or_charm=item,
                seal_or_charm_filters=self.seal_filters,
                section_name="Seals",
                mythic_name="Mythic Seal",
            )

        if item.item_type == ItemType.Charm:
            return self._check_seal_charm_filters(
                seal_or_charm=item,
                seal_or_charm_filters=self.charm_filters,
                section_name="Charms",
                mythic_name="Mythic Charm",
            )

        if item.item_type is None or item.power is None:
            return res

        keep_affixes = self._check_affixes(item)
        if keep_affixes.keep:
            return keep_affixes
        if item.rarity == ItemRarity.Legendary:
            res = self._check_aspect_upgrades(item)
        elif item.rarity == ItemRarity.Unique:
            res = self._check_global_unique_filter(item)
        elif item.rarity == ItemRarity.Mythic:
            # We always keep mythics
            res = FilterResult(keep=True, matched=[MatchedFilter(profile="Mythics always kept", aspect_match=True)])

        # After checking all possible options, if we still don't match, we check for a cosmetic upgrade
        if not res.keep:
            return self._check_cosmetic(item)

        return res
