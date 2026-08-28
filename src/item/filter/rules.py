"""Snapshots passed between profile loading and item evaluation."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.settings import AspectFilterType, CosmeticFilterType, UnfilteredUniquesType

if TYPE_CHECKING:
    from collections.abc import Mapping
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


@dataclass(frozen=True)
class LoadedRules:
    """The complete set of profile rules loaded at one point in time.

    The mappings contain the validated profile models.  The snapshot itself is
    replaced as a whole when profiles are reloaded, so an evaluator never sees
    a partially loaded collection of rules.
    """

    affix_filters: Mapping[str, list[DynamicItemFilterModel]]
    aspect_upgrade_filters: Mapping[str, list[str]]
    paragon_filters: Mapping[str, ParagonPayloadModel]
    global_unique_filters: Mapping[str, list[GlobalUniqueModel]]
    seal_filters: Mapping[str, list[DynamicSealFilterModel]]
    charm_filters: Mapping[str, list[DynamicCharmFilterModel]]
    sigil_filters: Mapping[str, SigilFilterModel]
    tribute_filters: Mapping[str, TributeFilterModel]
    all_file_paths: tuple[Path, ...] = ()

    @classmethod
    def empty(cls) -> LoadedRules:
        """Create an independent empty snapshot for an evaluator or test."""
        return cls({}, {}, {}, {}, {}, {}, {}, {})

    @property
    def has_profile_rules(self) -> bool:
        """Whether any loaded profile section can affect item evaluation."""
        return any(
            (
                self.affix_filters,
                self.aspect_upgrade_filters,
                self.paragon_filters,
                self.global_unique_filters,
                self.seal_filters,
                self.charm_filters,
                self.sigil_filters,
                self.tribute_filters,
            )
        )


@dataclass(frozen=True)
class EvaluationSettings:
    """Settings that affect a single item filtering decision."""

    filter_equipment: bool = True
    filter_sigils: bool = True
    filter_tributes: bool = True
    filter_seals: bool = True
    filter_charms: bool = True
    handle_cosmetics: CosmeticFilterType = CosmeticFilterType.ignore
    keep_aspects: AspectFilterType = AspectFilterType.upgrade
    handle_uniques: UnfilteredUniquesType = UnfilteredUniquesType.favorite
    ignore_escalation_sigils: bool = True

    @classmethod
    def from_settings(cls, settings: Settings) -> EvaluationSettings:
        """Copy evaluation settings from the application's mutable settings."""
        general = settings.general
        return cls(
            filter_equipment=general.filter_equipment,
            filter_sigils=general.filter_sigils,
            filter_tributes=general.filter_tributes,
            filter_seals=general.filter_seals,
            filter_charms=general.filter_charms,
            handle_cosmetics=general.handle_cosmetics,
            keep_aspects=general.keep_aspects,
            handle_uniques=general.handle_uniques,
            ignore_escalation_sigils=general.ignore_escalation_sigils,
        )
