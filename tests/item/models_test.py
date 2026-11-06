from src.game_data import ItemType
from src.item.data.affix import Affix
from src.item.models import FilterResult, Item, MatchedFilter


def test_item_equality_includes_item_fields() -> None:
    item = Item(name="helm", item_type=ItemType.Helm, affixes=[Affix(name="armor")])
    assert item == Item(name="helm", item_type=ItemType.Helm, affixes=[Affix(name="armor")])
    assert item != Item(name="helm", item_type=ItemType.Boots, affixes=[Affix(name="armor")])


def test_filter_result_keeps_matched_profile() -> None:
    result = FilterResult(True, [MatchedFilter("profile", [Affix(name="armor")])])
    assert result.matched[0].profile == "profile"


def test_filter_result_can_represent_a_skipped_item() -> None:
    result = FilterResult(keep=False, matched=[], skipped=True)

    assert result.skipped
    assert not result.keep
    assert result.matched == []


def test_item_equality_ignores_original_name_but_not_other_fields() -> None:
    assert Item(name="helm", original_name="a") == Item(name="helm", original_name="b")
    assert Item(name="helm", power=800) != Item(name="helm", power=750)
    assert Item(name="helm") != "helm"
