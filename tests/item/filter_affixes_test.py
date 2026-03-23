from src.item.filter_affixes import evaluate_affix_profiles
from tests.item.filter.data import filters
from tests.item.filter.data.affixes import affixes


def test_evaluate_affix_profiles_matches_existing_affix_fixtures():
    for _name, result, item in affixes:
        test_result = evaluate_affix_profiles(item, {filters.affix.name: filters.affix.Affixes})
        assert sorted(match.profile for match in test_result.matched) == sorted(result)


def test_evaluate_affix_profiles_returns_keep_when_no_filters_exist():
    _name, _result, item = affixes[0]

    test_result = evaluate_affix_profiles(item, {})

    assert test_result.keep is True
    assert test_result.matched == []
