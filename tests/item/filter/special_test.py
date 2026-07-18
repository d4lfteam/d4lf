import logging
import typing

import pytest
from natsort import natsorted

from src.item import Item, ItemRarity, ItemType
from src.profiles import SigilPriority, TributeFilterModel

from .conftest import (
    _create_mocked_filter,
    filters,
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
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(("_name", "result", "item"), natsorted(sigils), ids=[name for name, _, _ in natsorted(sigils)])
def test_sigils(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil.name: filters.sigil.sigils}
    assert natsorted([match.profile.split(".")[0] for match in test_filter.should_keep(item).matched]) == natsorted(
        result
    )


def test_sigil_empty_lists(mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil_whitelist_only.name: filters.sigil_whitelist_only.sigils}
    assert test_filter.should_keep(sigil_jalal).matched == []
    assert test_filter.should_keep(sigil_priority).matched[0].profile == filters.sigil_whitelist_only.name
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil_blacklist_only.name: filters.sigil_blacklist_only.sigils}
    assert test_filter.should_keep(sigil_jalal).matched[0].profile == filters.sigil_blacklist_only.name
    assert test_filter.should_keep(sigil_priority).matched == []


def test_sigil_priority(mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil_priority.name: filters.sigil_priority.sigils}
    assert test_filter.should_keep(sigil_priority).matched == []
    test_filter.sigil_filters[next(iter(test_filter.sigil_filters))].priority = SigilPriority.whitelist
    assert test_filter.should_keep(sigil_priority).matched[0].profile == filters.sigil_priority.name


def test_mythic_sigil_always_kept(mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil.name: filters.sigil.sigils}
    assert test_filter.should_keep(sigil_mythic_fallback).matched[0].profile == "Mythic Sigil"


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(tributes), ids=[name for name, _, _ in natsorted(tributes)]
)
def test_tributes(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    tribute_filter = filters.tributes.tributes
    if tribute_filter is None:
        pytest.fail("tribute fixture must define a filter")
    test_filter.tribute_filters = {filters.tributes.name: tribute_filter}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


def test_tribute_name_only_filter_ignores_rarity(mocker: MockerFixture):
    """name-only filter: kept when name matches, regardless of rarity."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.tribute_filters = {"p": TributeFilterModel(name=["tribute_of_harmony"])}

    assert test_filter.should_keep(
        Item(name="tribute_of_harmony", rarity=ItemRarity.Magic, item_type=ItemType.Tribute)
    ).keep
    assert test_filter.should_keep(
        Item(name="tribute_of_harmony", rarity=ItemRarity.Legendary, item_type=ItemType.Tribute)
    ).keep
    assert not test_filter.should_keep(
        Item(name="tribute_of_fake", rarity=ItemRarity.Legendary, item_type=ItemType.Tribute)
    ).keep


def test_tribute_rarity_only_filter_ignores_name(mocker: MockerFixture):
    """rarity-only filter: kept when rarity matches, regardless of name."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.tribute_filters = {"p": TributeFilterModel(rarities=[ItemRarity.Legendary])}

    assert test_filter.should_keep(
        Item(name="tribute_of_harmony", rarity=ItemRarity.Legendary, item_type=ItemType.Tribute)
    ).keep
    assert test_filter.should_keep(
        Item(name="tribute_of_fake", rarity=ItemRarity.Legendary, item_type=ItemType.Tribute)
    ).keep
    assert not test_filter.should_keep(
        Item(name="tribute_of_harmony", rarity=ItemRarity.Magic, item_type=ItemType.Tribute)
    ).keep


def test_tribute_empty_filter_keeps_nothing(mocker: MockerFixture):
    """Tributes: {} — filter key present but no constraints: keep nothing (except mythics)."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.tribute_filters = {"p": TributeFilterModel()}

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


def test_sigil_rarity_gate_keeps_matching_rarity(mocker: MockerFixture):
    """A sigil whose derived rarity matches the gate passes through."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil_rarity_rare_only.name: filters.sigil_rarity_rare_only.sigils}
    assert test_filter.should_keep(sigil_derived_rare).matched[0].profile == filters.sigil_rarity_rare_only.name


def test_sigil_rarity_gate_drops_non_matching_rarity(mocker: MockerFixture):
    """A sigil whose derived rarity does NOT match the gate is dropped."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil_rarity_rare_only.name: filters.sigil_rarity_rare_only.sigils}
    assert test_filter.should_keep(sigil_derived_legendary).matched == []


def test_sigil_rarity_gate_drops_unknown_rarity(mocker: MockerFixture, caplog):
    """A sigil whose rarity cannot be derived is dropped when the gate is active (fail-closed)."""
    with caplog.at_level(logging.DEBUG, logger="src.item.sigil_rules"):
        test_filter = _create_mocked_filter(mocker)
        test_filter.sigil_filters = {filters.sigil_rarity_rare_only.name: filters.sigil_rarity_rare_only.sigils}
        result = test_filter.should_keep(sigil_unknown_rarity)
    assert result.matched == []
    assert any("Could not resolve sigil rarity" in r.message for r in caplog.records)


def test_sigil_rarity_gate_empty_passes_all(mocker: MockerFixture):
    """When rarities list is empty, all sigils pass (regression — preserves current behavior)."""
    test_filter = _create_mocked_filter(mocker)
    # Use a filter that only has blacklist, no rarity gate
    test_filter.sigil_filters = {filters.sigil_blacklist_only.name: filters.sigil_blacklist_only.sigils}
    # sigil_derived_rare is not blacklisted — should pass
    assert test_filter.should_keep(sigil_derived_rare).matched[0].profile == filters.sigil_blacklist_only.name


def test_sigil_rarity_and_blacklist_drops_blacklisted(mocker: MockerFixture):
    """A sigil that passes the rarity gate but is blacklisted is still dropped."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {
        filters.sigil_rarity_rare_with_blacklist.name: filters.sigil_rarity_rare_with_blacklist.sigils
    }
    # sigil_rare_blacklisted is Rare (passes rarity gate) but has reduce_cooldowns_on_kill (blacklisted)
    assert test_filter.should_keep(sigil_rare_blacklisted).matched == []


def test_sigil_rarity_and_whitelist_drops_whitelisted_wrong_rarity(mocker: MockerFixture):
    """A whitelisted sigil whose rarity fails the gate is still dropped (rarity ANDs with whitelist)."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {
        filters.sigil_rarity_rare_with_whitelist.name: filters.sigil_rarity_rare_with_whitelist.sigils
    }
    # sigil_derived_legendary has jalals_vigil (whitelisted) but is Legendary — rarity gate drops it
    assert test_filter.should_keep(sigil_derived_legendary).matched == []
    # sigil_derived_rare has jalals_vigil (whitelisted) and is Rare — passes both
    assert (
        test_filter.should_keep(sigil_derived_rare).matched[0].profile == filters.sigil_rarity_rare_with_whitelist.name
    )


def test_sigil_rarity_and_blacklist_keeps_rare_not_blacklisted(mocker: MockerFixture):
    """A sigil that passes the rarity gate and is not blacklisted is kept."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {
        filters.sigil_rarity_rare_with_blacklist.name: filters.sigil_rarity_rare_with_blacklist.sigils
    }
    # sigil_derived_rare is Rare and not blacklisted — should pass
    assert (
        test_filter.should_keep(sigil_derived_rare).matched[0].profile == filters.sigil_rarity_rare_with_blacklist.name
    )


def test_sigil_rarity_gate_drops_legendary_regardless_of_blacklist_state(mocker: MockerFixture):
    """A sigil failing the rarity gate is dropped even when no blacklist entry matches it."""
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {
        filters.sigil_rarity_rare_with_blacklist.name: filters.sigil_rarity_rare_with_blacklist.sigils
    }
    # sigil_derived_legendary is Legendary — fails rarity gate, dropped regardless of blacklist
    assert test_filter.should_keep(sigil_derived_legendary).matched == []
