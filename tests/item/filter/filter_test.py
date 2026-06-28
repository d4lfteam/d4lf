from __future__ import annotations

import logging
import sys
import typing

import pytest
from natsort import natsorted

if sys.platform == "darwin":
    pytest.skip("Windows-only filter test module", allow_module_level=True)

from src.config.loader import IniConfigLoader
from src.config.profile_models import ParagonPayloadModel, ProfileModel, SigilPriority
from src.config.settings_models import AspectFilterType
from src.gui.importer.gui_common import save_as_profile
from src.item.data.affix import Affix
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.filter import Filter, FilterResult
from src.item.models import Item
from tests.item.filter.data import filters
from tests.item.filter.data.affixes import affixes
from tests.item.filter.data.aspects import aspects
from tests.item.filter.data.charms import charms
from tests.item.filter.data.seals import seals
from tests.item.filter.data.sigils import (
    sigil_derived_legendary,
    sigil_derived_rare,
    sigil_jalal,
    sigil_mythic_fallback,
    sigil_priority,
    sigil_rare_blacklisted,
    sigil_unknown_rarity,
    sigils,
)
from tests.item.filter.data.tributes import tributes
from tests.item.filter.data.uniques import global_uniques, simple_mythics, uniques_with_affixes

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _create_mocked_filter(mocker: MockerFixture) -> Filter:
    filter_obj = Filter()
    # Filter is singleton so we need to reset the filters to be safe
    filter_obj.affix_filters = {}
    filter_obj.aspect_upgrade_filters = {}
    filter_obj.paragon_filters = {}
    filter_obj.global_unique_filters = {}
    filter_obj.seal_filters = {}
    filter_obj.charm_filters = {}
    filter_obj.sigil_filters = {}
    filter_obj.tribute_filters = {}
    filter_obj.files_loaded = True
    mocker.patch.object(filter_obj, "_did_files_change", return_value=False)
    return filter_obj


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(affixes), ids=[name for name, _, _ in natsorted(affixes)]
)
def test_affixes(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.affix_filters = {filters.affix.name: filters.affix.affixes}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(aspects), ids=[name for name, _, _ in natsorted(aspects)]
)
def test_aspects(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    general_mock = mocker.patch.object(IniConfigLoader(), "_general")
    general_mock.keep_aspects = AspectFilterType.upgrade
    mocker.patch.object(test_filter, "_check_affixes", return_value=FilterResult(keep=False, matched=[]))
    test_filter.aspect_upgrade_filters = {filters.aspects_filters.name: filters.aspects_filters.aspect_upgrades}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(global_uniques), ids=[name for name, _, _ in natsorted(global_uniques)]
)
def test_global_uniques(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.global_unique_filters = {filters.global_unique.name: filters.global_unique.global_uniques}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


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
    test_filter.tribute_filters = {filters.tributes.name: filters.tributes.tributes}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(("_name", "result", "item"), natsorted(seals), ids=[name for name, _, _ in natsorted(seals)])
def test_seals(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.seal_filters = {filters.seal_charm.name: filters.seal_charm.seals}
    matches = test_filter.should_keep(item).matched
    assert natsorted([match.profile for match in matches]) == natsorted(result)
    for match in matches:
        if match.profile.startswith("seal_charm.Seals."):
            assert match.matched_affixes


@pytest.mark.parametrize(("_name", "result", "item"), natsorted(charms), ids=[name for name, _, _ in natsorted(charms)])
def test_charms(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.charm_filters = {filters.seal_charm.name: filters.seal_charm.charms}
    matches = test_filter.should_keep(item).matched
    assert natsorted([match.profile for match in matches]) == natsorted(result)
    for match in matches:
        if match.profile in {"seal_charm.Charms.basic_magic", "seal_charm.Charms.speed"}:
            assert match.matched_affixes
        if match.profile == "seal_charm.Charms.wanted_set":
            assert match.set_match
        if match.profile == "seal_charm.Charms.wanted_unique_aspect":
            assert match.aspect_match


@pytest.mark.parametrize(
    ("_name", "result", "item"),
    natsorted(uniques_with_affixes),
    ids=[name for name, _, _ in natsorted(uniques_with_affixes)],
)
def test_uniques_with_affixes(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.affix_filters = {filters.unique_affixes.name: filters.unique_affixes.affixes}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(simple_mythics), ids=[name for name, _, _ in natsorted(simple_mythics)]
)
def test_mythic_always_kept(_name: str, result: bool, item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.global_unique_filters = {filters.always_keep_mythics.name: filters.always_keep_mythics.global_uniques}
    assert test_filter.should_keep(item).keep == result


@pytest.mark.parametrize(
    ("rarity", "expected"),
    [
        # Rare matches the rarity-gated RareOnly rule AND the ungated AnyRarity rule.
        (ItemRarity.Rare, {"rarity_test.RareOnly", "rarity_test.AnyRarity"}),
        # Legendary fails the RareOnly gate but the empty-rarity AnyRarity rule still matches (regression).
        (ItemRarity.Legendary, {"rarity_test.AnyRarity"}),
    ],
)
def test_affix_rarity_gate(rarity: ItemRarity, expected: set[str], mocker: MockerFixture):
    boots = Item(
        item_type=ItemType.Boots,
        power=900,
        rarity=rarity,
        affixes=[Affix(name="movement_speed", value=10)],
        inherent=[],
    )
    test_filter = _create_mocked_filter(mocker)
    test_filter.affix_filters = {filters.affix_rarity.name: filters.affix_rarity.affixes}
    assert {m.profile for m in test_filter.should_keep(boots).matched} == expected


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
    with caplog.at_level(logging.DEBUG, logger="src.item.filter"):
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


def test_filter_loads_typed_paragon_payload(tmp_path, mock_ini_loader: IniConfigLoader, mocker: MockerFixture) -> None:
    mock_ini_loader._user_dir = tmp_path
    mock_ini_loader.general.profiles = ["typed_paragon"]

    profile = ProfileModel(
        name="typed_paragon",
        Paragon={
            "Name": "Build Name",
            "ParagonBoardsList": [
                [{"Name": "Starting Board", "Glyph": "glyph_name", "Rotation": 0, "Nodes": [False] * 441}]
            ],
        },
    )
    save_as_profile(file_name="typed_paragon", profile=profile, url="https://example.invalid")

    test_filter = _create_mocked_filter(mocker)
    test_filter.files_loaded = False
    test_filter.load_files()

    assert isinstance(test_filter.get_paragon_filters()["typed_paragon"], ParagonPayloadModel)
