import typing

import pytest
from natsort import natsorted

from src.item import Affix, FilterResult, Item
from src.profiles import AffixFilterCountModel, AffixFilterModel
from src.settings import AspectFilterType, get_settings

from .conftest import _create_mocked_filter, _rules, aspects, charms, filters, seals

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(aspects), ids=[name for name, _, _ in natsorted(aspects)]
)
def test_aspects(_name: str, result: list[str], item: Item, mocker: MockerFixture) -> None:
    test_filter = _create_mocked_filter(mocker)
    mocker.patch.object(get_settings().general, "keep_aspects", AspectFilterType.upgrade)
    mocker.patch.object(test_filter, "_check_affixes", return_value=FilterResult(keep=False, matched=[]))
    test_filter.rules = _rules(
        aspect_upgrade_filters={filters.aspects_filters.name: filters.aspects_filters.aspect_upgrades}
    )
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(("_name", "result", "item"), natsorted(seals), ids=[name for name, _, _ in natsorted(seals)])
def test_seals(_name: str, result: list[str], item: Item, mocker: MockerFixture) -> None:
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(seal_filters={filters.seal_charm.name: filters.seal_charm.seals})
    matches = test_filter.should_keep(item).matched
    assert natsorted([match.profile for match in matches]) == natsorted(result)
    for match in matches:
        if match.profile.startswith("seal_charm.Seals."):
            assert match.matched_affixes


@pytest.mark.parametrize(("_name", "result", "item"), natsorted(charms), ids=[name for name, _, _ in natsorted(charms)])
def test_charms(_name: str, result: list[str], item: Item, mocker: MockerFixture) -> None:
    test_filter = _create_mocked_filter(mocker)
    test_filter.rules = _rules(charm_filters={filters.seal_charm.name: filters.seal_charm.charms})
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
    ("expected", "max_count", "item_affixes", "missing"),
    [
        (
            [AffixFilterModel(name="dexterity"), AffixFilterModel(name="armor"), AffixFilterModel(name="maximum_life")],
            3,
            [Affix(name="dexterity"), Affix(name="armor")],
            ["maximum_life"],
        ),
        (
            [AffixFilterModel(name="dexterity"), AffixFilterModel(name="armor"), AffixFilterModel(name="maximum_life")],
            2,
            [Affix(name="dexterity"), Affix(name="armor"), Affix(name="maximum_life")],
            [],
        ),
        (
            [AffixFilterModel(name="armor"), AffixFilterModel(name="armor")],
            2,
            [Affix(name="armor"), Affix(name="dexterity")],
            ["armor"],
        ),
        (
            [AffixFilterModel(name="armor", value=50)],
            1,
            [Affix(name="armor", value=40, min_value=30, max_value=60)],
            ["armor"],
        ),
        (
            [AffixFilterModel(name="armor", min_percent_of_affix=80)],
            1,
            [Affix(name="armor", value=40, min_value=30, max_value=60)],
            ["armor"],
        ),
        (
            [AffixFilterModel(name="armor", value=50)],
            1,
            [Affix(name="armor", value=55, min_value=30, max_value=60)],
            [],
        ),
    ],
    ids=[
        "absent_affix",
        "present_affix_beyond_max_count",
        "duplicate_requirement",
        "below_value_threshold",
        "below_min_percent_of_affix",
        "meets_value_threshold",
    ],
)
def test_missing_affix_names(
    expected: list[AffixFilterModel],
    max_count: int,
    item_affixes: list[Affix],
    missing: list[str],
    mocker: MockerFixture,
) -> None:
    pool = [AffixFilterCountModel(count=expected, min_count=1, max_count=max_count)]

    assert _create_mocked_filter(mocker)._missing_affix_names(pool, item_affixes) == missing
