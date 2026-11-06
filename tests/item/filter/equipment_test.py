import pytest
from natsort import natsorted

from src.game_data import ItemRarity, ItemType
from src.item import Affix, Item
from src.item.filter.evaluator import FilterEvaluator
from src.item.filter.rules import EvaluationSettings
from src.profiles import AffixFilterCountModel, AffixFilterModel, ItemFilterModel, ProfileModel

from .conftest import _rules, affixes, filters, global_uniques, simple_mythics, uniques_with_affixes


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(affixes), ids=[name for name, _, _ in natsorted(affixes)]
)
def test_affixes(_name: str, result: list[str], item: Item) -> None:
    test_filter = FilterEvaluator(_rules(affix_filters={filters.affix.name: filters.affix.affixes}))
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(global_uniques), ids=[name for name, _, _ in natsorted(global_uniques)]
)
def test_global_uniques(_name: str, result: list[str], item: Item) -> None:
    test_filter = FilterEvaluator(
        _rules(global_unique_filters={filters.global_unique.name: filters.global_unique.global_uniques})
    )
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(
    ("_name", "result", "item"),
    natsorted(uniques_with_affixes),
    ids=[name for name, _, _ in natsorted(uniques_with_affixes)],
)
def test_uniques_with_affixes(_name: str, result: list[str], item: Item) -> None:
    test_filter = FilterEvaluator(_rules(affix_filters={filters.unique_affixes.name: filters.unique_affixes.affixes}))
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(simple_mythics), ids=[name for name, _, _ in natsorted(simple_mythics)]
)
def test_mythic_always_kept(_name: str, result: bool, item: Item) -> None:
    test_filter = FilterEvaluator(
        _rules(global_unique_filters={filters.always_keep_mythics.name: filters.always_keep_mythics.global_uniques})
    )
    assert test_filter.should_keep(item).keep == result


def test_enabled_equipment_keeps_matches_and_rejects_non_matches() -> None:
    rules = _rules(affix_filters={"profile": filters.affix.affixes})
    test_filter = FilterEvaluator(rules)
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

    disabled_filter = FilterEvaluator(rules, EvaluationSettings(filter_equipment=False))
    assert disabled_filter.should_keep(matching).skipped
    assert disabled_filter.should_keep(non_matching).skipped


def test_affix_match_reports_filter_affixes_missing_from_item() -> None:
    profile = ProfileModel(
        name="build",
        affixes=[
            {
                "Helm": ItemFilterModel(
                    item_type=[ItemType.Helm],
                    affix_pool=[
                        AffixFilterCountModel(
                            count=[
                                AffixFilterModel(name="dexterity"),
                                AffixFilterModel(name="maximum_resource"),
                                AffixFilterModel(name="armor"),
                                AffixFilterModel(name="maximum_life"),
                            ],
                            min_count=3,
                        )
                    ],
                )
            }
        ],
    )
    test_filter = FilterEvaluator(_rules(affix_filters={profile.name: profile.affixes}))
    helm = Item(
        item_type=ItemType.Helm,
        power=900,
        rarity=ItemRarity.Legendary,
        affixes=[
            Affix(name="dexterity"),
            Affix(name="maximum_resource"),
            Affix(name="armor"),
            Affix(name="shadow_resistance"),
        ],
    )

    result = test_filter.should_keep(helm)

    assert [affix.name for affix in result.matched[0].matched_affixes] == ["dexterity", "maximum_resource", "armor"]
    assert result.matched[0].missing_affixes == ["maximum_life"]


def test_affix_match_reports_filter_inherents_missing_from_item() -> None:
    profile = ProfileModel(
        name="build",
        affixes=[
            {
                "Helm": ItemFilterModel(
                    item_type=[ItemType.Helm],
                    affix_pool=[AffixFilterCountModel(count=[AffixFilterModel(name="dexterity")], min_count=1)],
                    inherent_pool=[
                        AffixFilterCountModel(
                            count=[AffixFilterModel(name="maximum_life"), AffixFilterModel(name="armor")], min_count=1
                        )
                    ],
                )
            }
        ],
    )
    test_filter = FilterEvaluator(_rules(affix_filters={profile.name: profile.affixes}))
    helm = Item(
        item_type=ItemType.Helm,
        power=900,
        rarity=ItemRarity.Legendary,
        affixes=[Affix(name="dexterity")],
        inherent=[Affix(name="armor")],
    )

    result = test_filter.should_keep(helm)

    assert [affix.name for affix in result.matched[0].matched_affixes] == ["dexterity", "armor"]
    assert result.matched[0].missing_affixes == ["maximum_life"]
