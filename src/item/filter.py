import logging
import pathlib
import sys
import time
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
from src.item.data.seasonal_attribute import SeasonalAttribute
from src.item.filter_affixes import evaluate_affix_profiles
from src.item.filter_categories import evaluate_sigil, evaluate_tribute
from src.item.filter_matchers import (
    match_affixes_count,
    match_affixes_sigils,
    match_affixes_uniques,
    match_aspect_is_in_percent_range,
    match_greater_affix_count,
    match_item_aspect_or_affix,
    match_item_power,
    match_item_type,
)
from src.item.filter_types import FilterResult, MatchedFilter
from src.item.filter_unique import evaluate_unique_item
from src.scripts.common import ASPECT_UPGRADES_LABEL, is_junk_rarity

if TYPE_CHECKING:
    from src.item.data.aspect import Aspect
    from src.item.models import Item

LOGGER = logging.getLogger(__name__)

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
        return evaluate_affix_profiles(item, self.affix_filters)

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
        return evaluate_sigil(item, self.sigil_filters, self._match_affixes_sigils)

    def _check_tribute(self, item: Item) -> FilterResult:
        return evaluate_tribute(item, self.tribute_filters)

    def _check_unique_item(self, item: Item) -> FilterResult:
        return evaluate_unique_item(item, self.unique_filters, IniConfigLoader().general.handle_uniques)

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
        return match_affixes_count(
            expected_affixes=expected_affixes,
            item_affixes=item_affixes,
            min_greater_affix_count=min_greater_affix_count,
            match_item_aspect_or_affix_func=self._match_item_aspect_or_affix,
        )

    @staticmethod
    def _match_affixes_sigils(
        expected_affixes: list[SigilConditionModel], sigil_name: str, sigil_affixes: list[Affix]
    ) -> bool:
        return match_affixes_sigils(expected_affixes, sigil_name, sigil_affixes)

    def _match_affixes_uniques(
        self, expected_affixes: list[AffixFilterModel], item_affixes: list[Affix], min_greater_affix_count: int = 0
    ) -> bool:
        return match_affixes_uniques(
            expected_affixes=expected_affixes,
            item_affixes=item_affixes,
            min_greater_affix_count=min_greater_affix_count,
            match_item_aspect_or_affix_func=self._match_item_aspect_or_affix,
        )

    @staticmethod
    def _match_greater_affix_count(expected_min_count: int, item_affixes: list[Affix]) -> bool:
        return match_greater_affix_count(expected_min_count, item_affixes)

    @staticmethod
    def _match_aspect_is_in_percent_range(expected_percent: int, item_aspect: Aspect) -> bool:
        return match_aspect_is_in_percent_range(expected_percent, item_aspect)

    @staticmethod
    def _match_item_aspect_or_affix(
        expected_aspect: AffixAspectFilterModel | None, item_aspect: Aspect | Affix, is_fixed_aspect_value: bool = False
    ) -> bool:
        return match_item_aspect_or_affix(expected_aspect, item_aspect, is_fixed_aspect_value)

    @staticmethod
    def _match_item_power(min_power: int, item_power: int, max_power: int = sys.maxsize) -> bool:
        return match_item_power(min_power, item_power, max_power)

    @staticmethod
    def _match_item_type(expected_item_types: list[ItemType], item_type: ItemType) -> bool:
        return match_item_type(expected_item_types, item_type)

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

        if item.item_type is None or item.power is None or (is_junk_rarity(item) and not item.cosmetic_upgrade):
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
