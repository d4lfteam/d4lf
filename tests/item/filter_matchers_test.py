from src.config.models import AffixFilterCountModel, AffixFilterModel, ComparisonType, SigilConditionModel
from src.item.data.affix import Affix, AffixType
from src.item.filter_matchers import (
    match_affixes_count,
    match_affixes_sigils,
    match_affixes_uniques,
    match_item_aspect_or_affix,
)


def test_match_affixes_sigils_respects_name_and_condition():
    expected = [SigilConditionModel(name="shadow_damage", condition=["iron_hold"])]
    affixes = [Affix(name="shadow_damage"), Affix(name="iron_hold")]

    assert match_affixes_sigils(expected, "some_sigil", affixes) is True
    assert match_affixes_sigils(expected, "some_sigil", [Affix(name="shadow_damage")]) is False


def test_match_affixes_count_returns_empty_when_min_count_not_met():
    expected = [
        AffixFilterCountModel(
            count=[AffixFilterModel(name="dexterity"), AffixFilterModel(name="strength")],
            minCount=2,
            maxCount=2,
        )
    ]
    item_affixes = [Affix(name="dexterity", value=20)]

    assert match_affixes_count(expected, item_affixes, 0, match_item_aspect_or_affix) == []


def test_match_affixes_uniques_rejects_missing_greater_affix_requirement():
    expected = [
        AffixFilterModel(name="cooldown_reduction", want_greater=True),
        AffixFilterModel(name="movement_speed"),
    ]
    item_affixes = [
        Affix(name="cooldown_reduction", type=AffixType.normal),
        Affix(name="movement_speed", type=AffixType.normal),
    ]

    assert match_affixes_uniques(expected, item_affixes, 1, match_item_aspect_or_affix) is False


def test_match_item_aspect_or_affix_honors_comparison_threshold():
    expected = AffixFilterModel(name="dexterity", value=10, comparison=ComparisonType.larger)

    assert match_item_aspect_or_affix(expected, Affix(name="dexterity", value=11)) is True
    assert match_item_aspect_or_affix(expected, Affix(name="dexterity", value=9)) is False
