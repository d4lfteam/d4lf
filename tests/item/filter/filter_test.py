import pytest
from natsort import natsorted
from pytest_mock import MockerFixture

import tests.item.filter.data.filters as filters
from src.config.models import SigilPriority
from src.item.filter import Filter, FilterResult
from src.item.models import Item
from tests.item.filter.data.affixes import affixes
from tests.item.filter.data.sigils import sigil_jalal, sigil_priority, sigils
from tests.item.filter.data.uniques import aspect_only_mythic_tests, simple_mythics, uniques


def _create_mocked_filter(mocker: MockerFixture) -> Filter:
    filter_obj = Filter()
    filter_obj.files_loaded = True
    mocker.patch.object(filter_obj, "_did_files_change", return_value=False)
    return filter_obj


@pytest.mark.parametrize(("name", "result", "item"), natsorted(affixes), ids=[name for name, _, _ in natsorted(affixes)])
def test_affixes(name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    mocker.patch("item.filter.Filter._check_aspect", return_value=FilterResult(keep=False, matched=[]))
    test_filter.affix_filters = {filters.affix.name: filters.affix.Affixes}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(("name", "result", "item"), natsorted(sigils), ids=[name for name, _, _ in natsorted(sigils)])
def test_sigils(name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil.name: filters.sigil.Sigils}
    assert natsorted([match.profile.split(".")[0] for match in test_filter.should_keep(item).matched]) == natsorted(result)


def test_sigil_empty_lists(mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil_whitelist_only.name: filters.sigil_whitelist_only.Sigils}
    assert test_filter.should_keep(sigil_jalal).matched == []
    assert test_filter.should_keep(sigil_priority).matched[0].profile == filters.sigil_whitelist_only.name
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil_blacklist_only.name: filters.sigil_blacklist_only.Sigils}
    assert test_filter.should_keep(sigil_jalal).matched[0].profile == filters.sigil_blacklist_only.name
    assert test_filter.should_keep(sigil_priority).matched == []


def test_sigil_priority(mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil_priority.name: filters.sigil_priority.Sigils}
    assert test_filter.should_keep(sigil_priority).matched == []
    test_filter.sigil_filters[next(iter(test_filter.sigil_filters))].priority = SigilPriority.whitelist
    assert test_filter.should_keep(sigil_priority).matched[0].profile == filters.sigil_priority.name


@pytest.mark.parametrize(("name", "result", "item"), natsorted(uniques), ids=[name for name, _, _ in natsorted(uniques)])
def test_uniques(name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.unique_filters = {filters.unique.name: filters.unique.Uniques}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(("name", "result", "item"), natsorted(simple_mythics), ids=[name for name, _, _ in natsorted(simple_mythics)])
def test_mythic_always_kept(name: str, result: bool, item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.unique_filters = {filters.always_keep_mythics.name: filters.always_keep_mythics.Uniques}
    assert test_filter.should_keep(item).keep == result


@pytest.mark.parametrize(
    ("name", "should_keep", "matched", "item"),
    natsorted(aspect_only_mythic_tests),
    ids=[name for name, _, _, _ in natsorted(aspect_only_mythic_tests)],
)
def test_unfiltered_unique_is_kept(name: str, should_keep: bool, matched: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.unique_filters = {filters.aspect_only_unique_filters.name: filters.aspect_only_unique_filters.Uniques}
    test_filter_result = test_filter.should_keep(item)
    assert natsorted([match.profile for match in test_filter_result.matched]) == natsorted(matched)
    assert test_filter_result.keep == should_keep
