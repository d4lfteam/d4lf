import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

from src.game_data import ItemRarity, ItemType, is_sigil
from src.item import ASPECT_UPGRADES_LABEL, MYTHICS_ALWAYS_KEPT_LABEL
from src.item.filter.equipment import FilterEquipmentMixin
from src.item.filter.matching import FilterContext, FilterMatchingMixin
from src.item.filter.special import FilterSpecialMixin
from src.item.models import FilterResult, MatchedFilter
from src.profiles import ProfileDocumentError, ProfileDocumentStore
from src.settings import get_settings

if TYPE_CHECKING:
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


@dataclass(frozen=True)
class ProfileLoadReport:
    """Summary emitted once when enabled profiles are skipped during a load."""

    skipped: tuple[str, ...]
    message: str


ProfileLoadListener = Callable[[ProfileLoadReport], None]


@dataclass(frozen=True)
class ProfileLoadFailure:
    name: str
    reason: Literal["missing", "invalid"]
    signature: tuple[int, int] | None


class Filter(FilterSpecialMixin, FilterEquipmentMixin, FilterMatchingMixin, FilterContext):
    affix_filters: dict[str, list[DynamicItemFilterModel]] = {}
    aspect_upgrade_filters: dict[str, list[str]] = {}
    paragon_filters: dict[str, ParagonPayloadModel] = {}
    global_unique_filters: dict[str, list[GlobalUniqueModel]] = {}
    seal_filters: dict[str, list[DynamicSealFilterModel]] = {}
    charm_filters: dict[str, list[DynamicCharmFilterModel]] = {}
    sigil_filters: dict[str, SigilFilterModel] = {}
    tribute_filters: dict[str, TributeFilterModel] = {}

    files_loaded: bool = False
    all_file_paths: list[Path] = []
    last_loaded: float | None = None
    last_profile_list: list[str] | None = None

    _initialized: bool = False
    _instance = None

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._profile_signatures: dict[Path, tuple[int, int]] = {}
        self._missing_profile_checks: dict[str, int] = {}
        self._missing_recheck_pending = False
        self._failure_state: tuple[ProfileLoadFailure, ...] = ()
        self._failure_listeners: list[ProfileLoadListener] = []
        self.load_failures: tuple[str, ...] = ()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _did_files_change(self) -> bool:
        if self.last_loaded is None:
            return True
        settings = get_settings()
        current_profiles = [p.strip() for p in settings.general.profiles if p.strip()]
        if self.last_profile_list != current_profiles:
            LOGGER.info(f"Profile list changed: {self.last_profile_list} → {current_profiles}")
            return True

        if self._missing_recheck_pending:
            self._missing_recheck_pending = False
            return True
        for profile_name in current_profiles:
            profile_path = settings.user_dir / "profiles" / f"{profile_name}.yaml"
            signature = self._profile_signature(profile_path)
            if signature != self._profile_signatures.get(profile_path):
                return True
        return False

    @staticmethod
    def _profile_signature(path: Path) -> tuple[int, int] | None:
        try:
            stat_result = path.stat()
        except OSError:
            return None
        return stat_result.st_mtime_ns, stat_result.st_size

    def register_profile_failure_listener(self, listener: ProfileLoadListener) -> None:
        if listener not in self._failure_listeners:
            self._failure_listeners.append(listener)

    def unregister_profile_failure_listener(self, listener: ProfileLoadListener) -> None:
        self._failure_listeners = [existing for existing in self._failure_listeners if existing != listener]

    def _emit_load_report(self, failures: list[ProfileLoadFailure]) -> None:
        failure_state = tuple(
            sorted(failures, key=lambda failure: (failure.name, failure.reason, failure.signature or ()))
        )
        self.load_failures = tuple(failure.name for failure in failure_state)
        if not failure_state or failure_state == self._failure_state:
            self._failure_state = failure_state
            return
        self._failure_state = failure_state
        names = ", ".join(failure.name for failure in failure_state)
        message = f"Skipped enabled profiles: {names}."
        if not any((
            self.affix_filters,
            self.aspect_upgrade_filters,
            self.paragon_filters,
            self.global_unique_filters,
            self.seal_filters,
            self.charm_filters,
            self.sigil_filters,
            self.tribute_filters,
        )):
            message += " Filtering is running without profile rules."
        report = ProfileLoadReport(skipped=tuple(failure.name for failure in failure_state), message=message)
        LOGGER.warning(message)
        for listener in list(self._failure_listeners):
            try:
                listener(report)
            except Exception:
                LOGGER.exception("Failed to notify profile load listener")

    def load_files(self):
        self.files_loaded = True
        self.affix_filters = {}
        self.aspect_upgrade_filters = {}
        self.paragon_filters = {}
        self.seal_filters = {}
        self.charm_filters = {}
        self.sigil_filters = {}
        self.tribute_filters = {}
        self.global_unique_filters = {}
        settings = get_settings()
        profiles = [p.strip() for p in settings.general.profiles if p.strip()]
        if not profiles:
            LOGGER.warning(
                "No profiles are currently loaded. Please load a profile via the Importer, Settings, or Edit Profile sections to begin using the tool."
            )
            self.last_loaded = time.time()
            self.last_profile_list = []
            self._profile_signatures = {}
            self._emit_load_report([])
            return

        custom_profile_path = settings.user_dir / "profiles"
        self.all_file_paths = []
        self._profile_signatures = {}
        failures: list[ProfileLoadFailure] = []
        missing_names: list[str] = []
        for profile_str in profiles:
            custom_file_path = custom_profile_path / f"{profile_str}.yaml"
            if custom_file_path.is_file():
                profile_path = custom_file_path
            else:
                LOGGER.error("Could not load profile %s. Checked: %s", profile_str, custom_file_path)
                failures.append(ProfileLoadFailure(profile_str, "missing", None))
                missing_names.append(profile_str)
                self._missing_profile_checks[profile_str] = self._missing_profile_checks.get(profile_str, 0) + 1
                self._missing_recheck_pending = self._missing_profile_checks[profile_str] < 2
                continue
            self.all_file_paths.append(profile_path)
            signature = self._profile_signature(profile_path)
            if signature is not None:
                self._profile_signatures[profile_path] = signature
            self._missing_profile_checks.pop(profile_str, None)
            try:
                data = ProfileDocumentStore.default().load(profile_path).profile
            except ProfileDocumentError, OSError:
                LOGGER.exception("Failed to load enabled profile %s", profile_str)
                failures.append(ProfileLoadFailure(profile_str, "invalid", signature))
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
            LOGGER.info((info_str + " ".join(sections)).rstrip())
        if missing_names:
            still_missing = [name for name in missing_names if self._missing_profile_checks.get(name, 0) >= 2]
            if still_missing:
                remaining = [name for name in profiles if name not in still_missing]
                settings.save_value("general", "profiles", ",".join(remaining))
                self._missing_recheck_pending = False
                profiles = remaining
        self.last_loaded = time.time()
        self.last_profile_list = profiles.copy()
        self._emit_load_report(failures)

    def get_paragon_filters(self) -> dict[str, ParagonPayloadModel]:
        """Return the loaded Paragon payloads, reloading profiles when needed."""
        if not self.files_loaded or self._did_files_change():
            self.load_files()
        return self.paragon_filters

    def _skipped_by_filter_override(self, item: Item) -> bool:
        settings = get_settings().general
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
        if not self.files_loaded or self._did_files_change():
            self.load_files()
        if self._skipped_by_filter_override(item):
            LOGGER.debug("%s -- Skipped by loot filter override", item.original_name)
            return FilterResult(keep=False, matched=[], skipped=True)
        res = FilterResult(keep=False, matched=[])
        if is_sigil(item.item_type):
            return self._check_sigil(item)
        if item.item_type == ItemType.Tribute:
            return self._check_tribute(item)
        if item.item_type == ItemType.HoradricSeal:
            return self._check_seal_charm_filters(item, self.seal_filters, "Seals", "Mythic Seal")
        if item.item_type == ItemType.Charm:
            return self._check_seal_charm_filters(item, self.charm_filters, "Charms", "Mythic Charm")
        if item.item_type is None or item.power is None:
            return res
        keep_affixes = self._check_affixes(item)
        if keep_affixes.keep:
            return keep_affixes
        if item.rarity == ItemRarity.Legendary:
            res = self._check_aspect_upgrades(item)
        elif item.rarity == ItemRarity.Unique:
            res = self._check_global_unique_filter(item)
        elif item.rarity == ItemRarity.Mythic:  # mythics are always kept
            res = FilterResult(keep=True, matched=[MatchedFilter(profile=MYTHICS_ALWAYS_KEPT_LABEL, aspect_match=True)])
        if not res.keep:  # then check for a cosmetic upgrade
            return self._check_cosmetic(item)
        return res
