from dataclasses import replace

from src.game_data import ItemRarity, ItemType
from src.item import Affix, Item
from src.item.filter.evaluator import FilterEvaluator
from src.item.filter.rules import EvaluationSettings, LoadedRules

from .conftest import filters


def test_evaluator_uses_supplied_rules_without_application_settings() -> None:
    rules = replace(LoadedRules.empty(), affix_filters={filters.affix.name: filters.affix.affixes})
    evaluator = FilterEvaluator(rules, EvaluationSettings())
    item = Item(
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

    result = evaluator.evaluate(item)

    assert result.keep
    assert result.matched[0].profile.startswith(f"{filters.affix.name}.")


def test_evaluator_applies_category_override_from_supplied_settings() -> None:
    evaluator = FilterEvaluator(LoadedRules.empty(), EvaluationSettings(filter_equipment=False))

    result = evaluator.should_keep(Item(item_type=ItemType.Helm, power=900, rarity=ItemRarity.Rare))

    assert result.skipped
    assert not result.keep
