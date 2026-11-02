import logging
import typing

import pytest
from natsort import natsorted

from src.game_data import ItemRarity, ItemType
from src.item import Affix, Item
from src.profiles import DynamicCharmFilterModel, DynamicSealFilterModel, SigilPriority, TributeFilterModel

from .conftest import (
    _create_mocked_filter,
    _patch_override_settings,
    _rules,
    charms,
    filters,
    seals,
    sigil_derived_legendary,
    sigil_derived_rare,
    sigil_jalal,
    sigil_mythic_fallback,
    sigil_priority,
    sigil_rare_blacklisted,
    sigil_unknown_rarity,
    sigils,
    tributes,
)

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture

    from src.item.filter.rules import LoadedRules


FILTERED_SPECIAL_CASES = (
    ("filter_sigils", _rules(sigil_filters={"profile": filters.sigil.sigils}), sigil_jalal, sigil_rare_blacklisted),
    (
        "filter_tributes",
        _rules(tribute_filters={"profile": TributeFilterModel(name=["tribute_of_harmony"])}),
        Item(name="tribute_of_harmony", item_type=ItemType.Tribute, rarity=ItemRarity.Magic),
        Item(name="tribute_of_fake", item_type=ItemType.Tribute, rarity=ItemRarity.Magic),
    ),
    (
        "filter_seals",
        _rules(seal_filters={"profile": filters.seal_charm.seals}),
        seals[0][2],
        Item(item_type=ItemType.HoradricSeal, rarity=ItemRarity.Rare),
    ),
    (
        "filter_charms",
        _rules(charm_filters={"profile": filters.seal_charm.charms}),
        charms[0][2],
        Item(item_type=ItemType.Charm, rarity=ItemRarity.Rare),
    ),
)


@pytest.mark.parametrize(("setting", "rules", "matching", "non_matching"), FILTERED_SPECIAL_CASES)
def test_enabled_special_categories_keep_matches_and_reject_non_matches(
    setting, rules, matching, non_matching, mocker
) -> None:
    settings = _patch_override_settings(mocker)
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = rules

    enabled_match = test_filter.should_keep(matching)
    enabled_non_match = test_filter.should_keep(non_matching)

    assert enabled_match.keep
    assert not enabled_match.skipped
    assert not enabled_non_match.keep
    assert not enabled_non_match.skipped

    setattr(settings.general, setting, False)
    assert test_filter.should_keep(matching).skipped
    assert test_filter.should_keep(non_matching).skipped


@pytest.mark.parametrize(("_name", "result", "item"), natsorted(sigils), ids=[name for name, _, _ in natsorted(sigils)])
def test_sigils(_name: str, result: list[str], item: Item, mocker: MockerFixture) -> None:
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(sigil_filters={filters.sigil.name: filters.sigil.sigils})
    assert natsorted([match.profile.split(".")[0] for match in test_filter.should_keep(item).matched]) == natsorted(
        result
    )


def test_sigil_empty_lists(mocker: MockerFixture) -> None:
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(sigil_filters={filters.sigil_whitelist_only.name: filters.sigil_whitelist_only.sigils})
    assert test_filter.should_keep(sigil_jalal).matched == []
    assert test_filter.should_keep(sigil_priority).matched[0].profile == filters.sigil_whitelist_only.name
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(sigil_filters={filters.sigil_blacklist_only.name: filters.sigil_blacklist_only.sigils})
    assert test_filter.should_keep(sigil_jalal).matched[0].profile == filters.sigil_blacklist_only.name
    assert test_filter.should_keep(sigil_priority).matched == []


def test_sigil_priority(mocker: MockerFixture) -> None:
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(sigil_filters={filters.sigil_priority.name: filters.sigil_priority.sigils})
    assert test_filter.should_keep(sigil_priority).matched == []
    test_filter.rules.sigil_filters[next(iter(test_filter.rules.sigil_filters))].priority = SigilPriority.whitelist
    assert test_filter.should_keep(sigil_priority).matched[0].profile == filters.sigil_priority.name


def test_sigil_rarity_whitelist_and_blacklist_respect_priority(mocker: MockerFixture) -> None:
    test_filter = _create_mocked_filter(mocker)
    profile_filter = filters.sigil_rarity_rare_with_whitelist.sigils.model_copy(deep=True)
    profile_filter.blacklist = [filters.sigil_rarity_rare_with_blacklist.sigils.blacklist[0]]
    test_filter.rules = _rules(sigil_filters={filters.sigil_rarity_rare_with_whitelist.name: profile_filter})

    assert test_filter.should_keep(sigil_rare_blacklisted).matched == []
    profile_filter.priority = SigilPriority.whitelist
    assert (
        test_filter.should_keep(sigil_rare_blacklisted).matched[0].profile
        == filters.sigil_rarity_rare_with_whitelist.name
    )


def test_mythic_sigil_always_kept(mocker: MockerFixture) -> None:
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(sigil_filters={filters.sigil.name: filters.sigil.sigils})
    assert test_filter.should_keep(sigil_mythic_fallback).matched[0].profile == "Mythic Sigil"


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(tributes), ids=[name for name, _, _ in natsorted(tributes)]
)
def test_tributes(_name: str, result: list[str], item: Item, mocker: MockerFixture) -> None:
    test_filter = _create_mocked_filter(mocker)
    tribute_filter = filters.tributes.tributes
    if tribute_filter is None:
        pytest.fail("tribute fixture must define a filter")
    test_filter.rules = _rules(tribute_filters={filters.tributes.name: tribute_filter})
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


def test_tribute_name_only_filter_ignores_rarity(mocker: MockerFixture) -> None:
    """name-only filter: kept when name matches, regardless of rarity."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(tribute_filters={"p": TributeFilterModel(name=["tribute_of_harmony"])})

    assert test_filter.should_keep(
        Item(name="tribute_of_harmony", rarity=ItemRarity.Magic, item_type=ItemType.Tribute)
    ).keep
    assert test_filter.should_keep(
        Item(name="tribute_of_harmony", rarity=ItemRarity.Legendary, item_type=ItemType.Tribute)
    ).keep
    assert not test_filter.should_keep(
        Item(name="tribute_of_fake", rarity=ItemRarity.Legendary, item_type=ItemType.Tribute)
    ).keep


def test_tribute_rarity_only_filter_ignores_name(mocker: MockerFixture) -> None:
    """rarity-only filter: kept when rarity matches, regardless of name."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(tribute_filters={"p": TributeFilterModel(rarities=[ItemRarity.Legendary])})

    assert test_filter.should_keep(
        Item(name="tribute_of_harmony", rarity=ItemRarity.Legendary, item_type=ItemType.Tribute)
    ).keep
    assert test_filter.should_keep(
        Item(name="tribute_of_fake", rarity=ItemRarity.Legendary, item_type=ItemType.Tribute)
    ).keep
    assert not test_filter.should_keep(
        Item(name="tribute_of_harmony", rarity=ItemRarity.Magic, item_type=ItemType.Tribute)
    ).keep


def test_tribute_empty_filter_keeps_nothing(mocker: MockerFixture) -> None:
    """Tributes: {} — filter key present but no constraints: keep nothing (except mythics)."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(tribute_filters={"p": TributeFilterModel()})

    assert not test_filter.should_keep(
        Item(name="tribute_of_harmony", rarity=ItemRarity.Magic, item_type=ItemType.Tribute)
    ).keep
    assert not test_filter.should_keep(
        Item(name="tribute_of_harmony", rarity=ItemRarity.Legendary, item_type=ItemType.Tribute)
    ).keep
    # mythic fallback still applies
    assert test_filter.should_keep(
        Item(name="tribute_of_harmony", rarity=ItemRarity.Mythic, item_type=ItemType.Tribute)
    ).keep


def test_sigil_rarity_gate_keeps_matching_and_drops_non_matching_rarity(mocker: MockerFixture) -> None:
    """A sigil whose derived rarity matches the gate passes through; a non-matching one is dropped."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(
        sigil_filters={filters.sigil_rarity_rare_only.name: filters.sigil_rarity_rare_only.sigils}
    )
    assert test_filter.should_keep(sigil_derived_rare).matched[0].profile == filters.sigil_rarity_rare_only.name
    assert test_filter.should_keep(sigil_derived_legendary).matched == []


def test_sigil_rarity_gate_drops_unknown_rarity(mocker: MockerFixture, caplog) -> None:
    """A sigil whose rarity cannot be derived is dropped when the gate is active (fail-closed)."""
    with caplog.at_level(logging.DEBUG, logger="src.game_data.sigil_rules"):
        test_filter = _create_mocked_filter(mocker)
        test_filter.rules = _rules(
            sigil_filters={filters.sigil_rarity_rare_only.name: filters.sigil_rarity_rare_only.sigils}
        )
        result = test_filter.should_keep(sigil_unknown_rarity)
    assert result.matched == []
    assert any("Could not resolve sigil rarity" in r.message for r in caplog.records)


def test_sigil_rarity_gate_empty_passes_all(mocker: MockerFixture) -> None:
    """When rarities list is empty, all sigils pass (regression — preserves current behavior)."""
    test_filter = _create_mocked_filter(mocker)
    # Use a filter that only has blacklist, no rarity gate
    test_filter.rules = _rules(sigil_filters={filters.sigil_blacklist_only.name: filters.sigil_blacklist_only.sigils})
    # sigil_derived_rare is not blacklisted — should pass
    assert test_filter.should_keep(sigil_derived_rare).matched[0].profile == filters.sigil_blacklist_only.name


def test_sigil_rarity_and_blacklist_drops_blacklisted(mocker: MockerFixture) -> None:
    """A sigil that passes the rarity gate but is blacklisted is still dropped."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(
        sigil_filters={filters.sigil_rarity_rare_with_blacklist.name: filters.sigil_rarity_rare_with_blacklist.sigils}
    )
    # sigil_rare_blacklisted is Rare (passes rarity gate) but has reduce_cooldowns_on_kill (blacklisted)
    assert test_filter.should_keep(sigil_rare_blacklisted).matched == []


def test_sigil_rarity_or_whitelist_keeps_whitelisted_wrong_rarity(mocker: MockerFixture) -> None:
    """A whitelist match keeps a sigil even when its derived rarity is not listed."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(
        sigil_filters={filters.sigil_rarity_rare_with_whitelist.name: filters.sigil_rarity_rare_with_whitelist.sigils}
    )
    # sigil_derived_legendary has jalals_vigil (whitelisted) but is Legendary.
    assert (
        test_filter.should_keep(sigil_derived_legendary).matched[0].profile
        == filters.sigil_rarity_rare_with_whitelist.name
    )
    # sigil_derived_rare has jalals_vigil (whitelisted) and is Rare.
    assert (
        test_filter.should_keep(sigil_derived_rare).matched[0].profile == filters.sigil_rarity_rare_with_whitelist.name
    )


def test_sigil_rarity_or_whitelist_keeps_unknown_rarity(mocker: MockerFixture) -> None:
    """A whitelist match also bypasses the fail-closed unknown-rarity gate."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(
        sigil_filters={filters.sigil_rarity_rare_with_whitelist.name: filters.sigil_rarity_rare_with_whitelist.sigils}
    )

    assert (
        test_filter.should_keep(sigil_unknown_rarity).matched[0].profile
        == filters.sigil_rarity_rare_with_whitelist.name
    )


def test_sigil_rarity_and_blacklist_keeps_rare_not_blacklisted(mocker: MockerFixture) -> None:
    """A sigil that passes the rarity gate and is not blacklisted is kept."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(
        sigil_filters={filters.sigil_rarity_rare_with_blacklist.name: filters.sigil_rarity_rare_with_blacklist.sigils}
    )
    # sigil_derived_rare is Rare and not blacklisted — should pass
    assert (
        test_filter.should_keep(sigil_derived_rare).matched[0].profile == filters.sigil_rarity_rare_with_blacklist.name
    )


def test_sigil_rarity_gate_drops_legendary_regardless_of_blacklist_state(mocker: MockerFixture) -> None:
    """A sigil failing the rarity gate is dropped even when no blacklist entry matches it."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(
        sigil_filters={filters.sigil_rarity_rare_with_blacklist.name: filters.sigil_rarity_rare_with_blacklist.sigils}
    )
    # sigil_derived_legendary is Legendary — fails rarity gate, dropped regardless of blacklist
    assert test_filter.should_keep(sigil_derived_legendary).matched == []


@pytest.mark.parametrize(
    ("rules_for", "item_type", "present", "absent"),
    [
        (
            lambda wanted: _rules(seal_filters={"profile": [DynamicSealFilterModel.model_validate(wanted)]}),
            ItemType.HoradricSeal,
            "damage",
            "strength",
        ),
        (
            lambda wanted: _rules(charm_filters={"profile": [DynamicCharmFilterModel.model_validate(wanted)]}),
            ItemType.Charm,
            "movement_speed",
            "to_basic_skills",
        ),
    ],
)
def test_seal_and_charm_match_reports_absent_affix_as_missing(
    rules_for: Callable[[dict[str, dict[str, list[dict[str, list[str] | int]]]]], LoadedRules],
    item_type: ItemType,
    present: str,
    absent: str,
    mocker: MockerFixture,
) -> None:
    test_filter = _create_mocked_filter(mocker)
    wanted = {"wanted": {"affixPool": [{"count": [present, absent], "min_count": 1}]}}
    test_filter.rules = rules_for(wanted)
    item = Item(item_type=item_type, rarity=ItemRarity.Rare, affixes=[Affix(name=present)])
    matched = test_filter.should_keep(item).matched[0]
    assert [affix.name for affix in matched.matched_affixes] == [present]
    assert matched.missing_affixes == [absent]
