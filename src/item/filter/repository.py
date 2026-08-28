"""Stateful loading and reload detection for item-filter profile rules."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from src.item import ASPECT_UPGRADES_LABEL
from src.item.filter.rules import LoadedRules
from src.profiles import ProfileDocumentError, ProfileDocumentStore
from src.settings import get_settings

if TYPE_CHECKING:
    from pathlib import Path

    from src.profiles import (
        DynamicCharmFilterModel,
        DynamicItemFilterModel,
        DynamicSealFilterModel,
        GlobalUniqueModel,
        ParagonPayloadModel,
        SigilFilterModel,
        TributeFilterModel,
    )
    from src.settings import Settings

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


@dataclass
class _MutableRules:
    affix_filters: dict[str, list[DynamicItemFilterModel]]
    aspect_upgrade_filters: dict[str, list[str]]
    paragon_filters: dict[str, ParagonPayloadModel]
    global_unique_filters: dict[str, list[GlobalUniqueModel]]
    seal_filters: dict[str, list[DynamicSealFilterModel]]
    charm_filters: dict[str, list[DynamicCharmFilterModel]]
    sigil_filters: dict[str, SigilFilterModel]
    tribute_filters: dict[str, TributeFilterModel]


class ProfileRulesRepository:
    """Own profile-file state and publish complete ``LoadedRules`` snapshots."""

    def __init__(self, settings_provider: Callable[[], Settings] | None = None) -> None:
        self._settings_provider = settings_provider or get_settings
        self._rules = LoadedRules.empty()
        self._files_loaded = False
        self._all_file_paths: tuple[Path, ...] = ()
        self._last_loaded: float | None = None
        self._last_profile_list: list[str] | None = None
        self._profile_signatures: dict[Path, tuple[int, int]] = {}
        self._missing_profile_checks: dict[str, int] = {}
        self._missing_recheck_pending = False
        self._failure_state: tuple[ProfileLoadFailure, ...] = ()
        self._failure_listeners: list[ProfileLoadListener] = []
        self.load_failures: tuple[str, ...] = ()

    @property
    def rules(self) -> LoadedRules:
        """Latest complete profile-rule snapshot."""
        return self._rules

    def replace_rules(self, rules: LoadedRules) -> None:
        """Replace rules for the facade's compatibility adapters and tests."""
        self._rules = rules
        self._all_file_paths = rules.all_file_paths

    @property
    def files_loaded(self) -> bool:
        return self._files_loaded

    @files_loaded.setter
    def files_loaded(self, value: bool) -> None:
        self._files_loaded = value

    @property
    def all_file_paths(self) -> list[Path]:
        return list(self._all_file_paths)

    @property
    def last_loaded(self) -> float | None:
        return self._last_loaded

    @last_loaded.setter
    def last_loaded(self, value: float | None) -> None:
        self._last_loaded = value

    @property
    def last_profile_list(self) -> list[str] | None:
        return None if self._last_profile_list is None else self._last_profile_list.copy()

    @last_profile_list.setter
    def last_profile_list(self, value: list[str] | None) -> None:
        self._last_profile_list = None if value is None else value.copy()

    @staticmethod
    def profile_signature(path: Path) -> tuple[int, int] | None:
        try:
            stat_result = path.stat()
        except OSError:
            return None
        return stat_result.st_mtime_ns, stat_result.st_size

    def did_files_change(self) -> bool:
        """Check enabled profile names, missing files, and file signatures."""
        if self._last_loaded is None:
            return True
        settings = self._settings_provider()
        current_profiles = [p.strip() for p in settings.general.profiles if p.strip()]
        if self._last_profile_list != current_profiles:
            LOGGER.info(f"Profile list changed: {self._last_profile_list} → {current_profiles}")
            return True

        if self._missing_recheck_pending:
            self._missing_recheck_pending = False
            return True
        for profile_name in current_profiles:
            profile_path = settings.user_dir / "profiles" / f"{profile_name}.yaml"
            signature = self.profile_signature(profile_path)
            if signature != self._profile_signatures.get(profile_path):
                return True
        return False

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
        if not self._rules.has_profile_rules:
            message += " Filtering is running without profile rules."
        report = ProfileLoadReport(skipped=tuple(failure.name for failure in failure_state), message=message)
        LOGGER.warning(message)
        for listener in list(self._failure_listeners):
            try:
                listener(report)
            except Exception:
                LOGGER.exception("Failed to notify profile load listener")

    def load_files(self) -> LoadedRules:
        """Load enabled profiles and publish one new rules snapshot."""
        settings = self._settings_provider()
        profiles = [p.strip() for p in settings.general.profiles if p.strip()]
        filters = _MutableRules({}, {}, {}, {}, {}, {}, {}, {})
        self._files_loaded = True
        self._all_file_paths = ()
        self._profile_signatures = {}
        failures: list[ProfileLoadFailure] = []
        missing_names: list[str] = []
        if not profiles:
            LOGGER.warning(
                "No profiles are currently loaded. Please load a profile via the Importer, Settings, or Edit Profile sections to begin using the tool."
            )
            self._last_loaded = time.time()
            self._last_profile_list = []
            self._missing_recheck_pending = False
            self._publish_rules(filters, ())
            self._emit_load_report([])
            return self._rules

        custom_profile_path = settings.user_dir / "profiles"
        profile_store = ProfileDocumentStore(profiles_dir=custom_profile_path, full_dump=False)
        all_file_paths: list[Path] = []
        for profile_str in profiles:
            custom_file_path = custom_profile_path / f"{profile_str}.yaml"
            if not custom_file_path.is_file():
                LOGGER.error("Could not load profile %s. Checked: %s", profile_str, custom_file_path)
                failures.append(ProfileLoadFailure(profile_str, "missing", None))
                missing_names.append(profile_str)
                self._missing_profile_checks[profile_str] = self._missing_profile_checks.get(profile_str, 0) + 1
                self._missing_recheck_pending = self._missing_profile_checks[profile_str] < 2
                continue
            all_file_paths.append(custom_file_path)
            signature = self.profile_signature(custom_file_path)
            if signature is not None:
                self._profile_signatures[custom_file_path] = signature
            self._missing_profile_checks.pop(profile_str, None)
            try:
                data = profile_store.load(custom_file_path).profile
            except ProfileDocumentError, OSError:
                LOGGER.exception("Failed to load enabled profile %s", profile_str)
                failures.append(ProfileLoadFailure(profile_str, "invalid", signature))
                continue

            info_str = f"Loading profile {profile_str}: "
            sections: list[str] = []
            if data.affixes:
                filters.affix_filters[data.name] = data.affixes
                sections.append("Affixes")
            if data.aspect_upgrades:
                filters.aspect_upgrade_filters[data.name] = data.aspect_upgrades
                sections.append(ASPECT_UPGRADES_LABEL)
            if data.seals:
                filters.seal_filters[data.name] = data.seals
                sections.append("Seals")
            if data.charms:
                filters.charm_filters[data.name] = data.charms
                sections.append("Charms")
            if data.sigils and (data.sigils.blacklist or data.sigils.whitelist or data.sigils.rarities):
                filters.sigil_filters[data.name] = data.sigils
                sections.append("Sigils")
            if data.tributes is not None:
                filters.tribute_filters[data.name] = data.tributes
                sections.append("Tributes")
            if data.global_uniques:
                filters.global_unique_filters[data.name] = data.global_uniques
                sections.append("GlobalUniques")
            if data.paragon:
                filters.paragon_filters[custom_file_path.stem] = data.paragon
                sections.append("Paragon")
            LOGGER.info((info_str + " ".join(sections)).rstrip())

        if missing_names:
            still_missing = [name for name in missing_names if self._missing_profile_checks.get(name, 0) >= 2]
            if still_missing:
                remaining = [name for name in profiles if name not in still_missing]
                settings.save_value("general", "profiles", ",".join(remaining))
                self._missing_recheck_pending = False
                profiles = remaining
        self._last_loaded = time.time()
        self._last_profile_list = profiles.copy()
        self._publish_rules(filters, tuple(all_file_paths))
        self._emit_load_report(failures)
        return self._rules

    def _publish_rules(self, filters: _MutableRules, paths: tuple[Path, ...]) -> None:
        self._all_file_paths = paths
        self._rules = LoadedRules(
            affix_filters=filters.affix_filters,
            aspect_upgrade_filters=filters.aspect_upgrade_filters,
            paragon_filters=filters.paragon_filters,
            global_unique_filters=filters.global_unique_filters,
            seal_filters=filters.seal_filters,
            charm_filters=filters.charm_filters,
            sigil_filters=filters.sigil_filters,
            tribute_filters=filters.tribute_filters,
            all_file_paths=paths,
        )
