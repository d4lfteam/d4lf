from __future__ import annotations

import typing

import pytest
from natsort import natsorted

from src.config.loader import IniConfigLoader
from src.config.profile_models import NameRarityFilterModel, SigilPriority
from src.config.settings_models import AspectFilterType
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.filter import Filter, FilterResult
from src.item.models import Item
from tests.item.filter.data import filters
from tests.item.filter.data.affixes import affixes
from tests.item.filter.data.aspects import aspects
from tests.item.filter.data.sigils import sigil_jalal, sigil_priority, sigils
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


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(tributes), ids=[name for name, _, _ in natsorted(tributes)]
)
def test_tributes(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.tribute_filters = {filters.tributes.name: filters.tributes.tributes}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(
    ("item", "filter_attr"),
    [
        (Item(item_type=ItemType.HoradricSeal, name="faint_seal", rarity=ItemRarity.Legendary), "seal_filters"),
        (Item(item_type=ItemType.Charm, name="faint_charm", rarity=ItemRarity.Rare), "charm_filters"),
    ],
)
def test_seal_or_charm_sections(item: Item, filter_attr: str, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    setattr(test_filter, filter_attr, {"spellcraft": [NameRarityFilterModel(name=item.name)]})

    assert test_filter.should_keep(item).matched[0].profile == "spellcraft"


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
