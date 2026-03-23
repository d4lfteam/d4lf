from src.config.models import AffixFilterModel, AspectUniqueFilterModel, ComparisonType, UnfilteredUniquesType, UniqueModel
from src.item.data.affix import Affix
from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.filter_unique import evaluate_unique_item
from src.item.models import Item
from tests.item.filter.data.uniques import TestUnique


def _evaluate(item: Item, unique_filters: dict[str, list], handle_uniques: UnfilteredUniquesType = UnfilteredUniquesType.favorite):
    return evaluate_unique_item(item=item, unique_filters=unique_filters, handle_uniques=handle_uniques)


def test_unique_item_without_filters_follows_handle_uniques():
    item = TestUnique(aspect=Aspect(name="black_river"), rarity=ItemRarity.Unique)

    assert _evaluate(item, {}, UnfilteredUniquesType.favorite).keep is True
    assert _evaluate(item, {}, UnfilteredUniquesType.junk).keep is False


def test_mythics_are_always_kept_without_filters():
    item = TestUnique(aspect=Aspect(name="black_river"), rarity=ItemRarity.Mythic)

    assert _evaluate(item, {}, UnfilteredUniquesType.junk).keep is True


def test_aspect_only_filters_fall_back_to_handle_uniques_when_no_aspect_matches():
    item = TestUnique(aspect=Aspect("crown_of_lucion"))
    unique_filters = {
        "aspect_only": [UniqueModel(aspect=AspectUniqueFilterModel(name="tibaults_will"), minPower=900)]
    }

    result = _evaluate(item, unique_filters, UnfilteredUniquesType.favorite)
    assert result.keep is True
    assert result.matched == []
    assert result.unique_aspect_in_profile is False
    assert result.all_unique_filters_are_aspects is True


def test_aspect_only_filters_respect_junk_mode_for_non_matching_items():
    item = TestUnique(aspect=Aspect("crown_of_lucion"))
    unique_filters = {
        "aspect_only": [UniqueModel(aspect=AspectUniqueFilterModel(name="tibaults_will"), minPower=900)]
    }

    result = _evaluate(item, unique_filters, UnfilteredUniquesType.junk)
    assert result.keep is False
    assert result.matched == []


def test_unique_profile_matches_use_alias_and_aspect_match():
    item = TestUnique(item_type=ItemType.Scythe, aspect=Aspect(name="black_river", value=128), rarity=ItemRarity.Mythic)
    unique_filters = {
        "test": [
            UniqueModel(
                aspect=AspectUniqueFilterModel(name="black_river", value=20, comparison=ComparisonType.larger),
                itemType=[ItemType.Scythe],
                minPower=900,
                profileAlias="alias_test",
            )
        ]
    }

    result = _evaluate(item, unique_filters)
    assert result.keep is True
    assert result.matched[0].profile == "alias_test.black_river"


def test_existing_unique_fixture_examples_can_be_evaluated():
    unique_filters = {
        "test": [
            UniqueModel(
                aspect=AspectUniqueFilterModel(name="soulbrand", value=20, comparison=ComparisonType.larger),
                itemType=[ItemType.Scythe, ItemType.Sword],
                minPower=900,
                affix=[AffixFilterModel(name="attack_speed", value=8.4)],
            )
        ]
    }

    item = TestUnique(
        item_type=ItemType.Scythe,
        aspect=Aspect(name="soulbrand", value=22),
        affixes=[Affix(name="attack_speed", value=9.6)],
    )
    result = _evaluate(item, unique_filters)
    assert result.keep is True
    assert result.matched[0].profile == "test.soulbrand"
