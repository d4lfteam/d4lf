import typing

import pytest
from natsort import natsorted

from src.game_data import ItemRarity, ItemType
from src.item import Affix, Item

from .conftest import (
    _create_mocked_filter,
    _patch_override_settings,
    affixes,
    filters,
    global_uniques,
    simple_mythics,
    uniques_with_affixes,
)

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(affixes), ids=[name for name, _, _ in natsorted(affixes)]
)
def test_affixes(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.affix_filters = {filters.affix.name: filters.affix.affixes}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(global_uniques), ids=[name for name, _, _ in natsorted(global_uniques)]
)
def test_global_uniques(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.global_unique_filters = {filters.global_unique.name: filters.global_unique.global_uniques}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


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


def test_enabled_equipment_keeps_matches_and_rejects_non_matches(mocker: MockerFixture):
    settings = _patch_override_settings(mocker)
    test_filter = _create_mocked_filter(mocker)
    test_filter.affix_filters = {"profile": filters.affix.affixes}
    matching = Item(
        item_type=ItemType.Helm,
        power=725,
        rarity=ItemRarity.Rare,
        affixes=[
            Affix(name="intelligence", value=10),
            Affix(name="cooldown_reduction", value=10),
            Affix(name="maximum_life", value=700),
            Affix(name="total_armor", value=10),
        ],
    )
    non_matching = Item(item_type=ItemType.Helm, power=725, rarity=ItemRarity.Rare)

    enabled_match = test_filter.should_keep(matching)
    enabled_non_match = test_filter.should_keep(non_matching)

    assert enabled_match.keep
    assert not enabled_match.skipped
    assert not enabled_non_match.keep
    assert not enabled_non_match.skipped

    settings.general.filter_equipment = False
    assert test_filter.should_keep(matching).skipped
    assert test_filter.should_keep(non_matching).skipped
