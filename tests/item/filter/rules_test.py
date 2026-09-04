from dataclasses import replace
from types import SimpleNamespace
from typing import cast

from src.item.filter.rules import EvaluationSettings, LoadedRules
from src.settings import AspectFilterType, CosmeticFilterType, Settings, UnfilteredUniquesType


def test_empty_rules_are_independent_snapshots() -> None:
    first = LoadedRules.empty()
    second = LoadedRules.empty()

    assert first == second
    assert first is not second
    assert first.affix_filters is not second.affix_filters
    assert not first.has_profile_rules


def test_loaded_rules_report_any_nonempty_profile_section() -> None:
    rules = replace(LoadedRules.empty(), affix_filters={"profile": []})

    assert rules.has_profile_rules


def test_evaluation_settings_copy_only_decision_settings() -> None:
    settings = SimpleNamespace(
        general=SimpleNamespace(
            filter_equipment=False,
            filter_sigils=True,
            filter_tributes=False,
            filter_seals=True,
            filter_charms=False,
            handle_cosmetics=CosmeticFilterType.junk,
            keep_aspects=AspectFilterType.none,
            handle_uniques=UnfilteredUniquesType.junk,
            ignore_escalation_sigils=False,
        )
    )

    snapshot = EvaluationSettings.from_settings(cast("Settings", settings))

    assert snapshot == EvaluationSettings(
        filter_equipment=False,
        filter_sigils=True,
        filter_tributes=False,
        filter_seals=True,
        filter_charms=False,
        handle_cosmetics=CosmeticFilterType.junk,
        keep_aspects=AspectFilterType.none,
        handle_uniques=UnfilteredUniquesType.junk,
        ignore_escalation_sigils=False,
    )
