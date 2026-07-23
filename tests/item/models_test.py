import json

from src.item.data.affix import Affix
from src.item.data.item_type import ItemType
from src.item.models import FilterResult, Item, ItemJSONEncoder, MatchedFilter


def test_item_equality_includes_item_fields():
    item = Item(name="helm", item_type=ItemType.Helm, affixes=[Affix(name="armor")])
    assert item == Item(name="helm", item_type=ItemType.Helm, affixes=[Affix(name="armor")])
    assert item != Item(name="helm", item_type=ItemType.Boots, affixes=[Affix(name="armor")])


def test_result_and_json_encoder():
    result = FilterResult(True, [MatchedFilter("profile", [Affix(name="armor")])])
    assert result.matched[0].profile == "profile"
    encoded = json.dumps(Item(name="helm", item_type=ItemType.Helm), cls=ItemJSONEncoder)
    assert '"item_type": "helm"' in encoded
