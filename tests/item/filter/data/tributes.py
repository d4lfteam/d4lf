from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.models import Item


class TestTribute(Item):
    def __init__(self, rarity=ItemRarity.Common, item_type=ItemType.Tribute, **kwargs):
        super().__init__(rarity=rarity, item_type=item_type, **kwargs)


tributes = [
    ("ok_1", ["tributes"], TestTribute(name="tribute_of_pride", rarity=ItemRarity.Magic)),
    ("ok_2", ["tributes"], TestTribute(name="tribute_of_mystique", rarity=ItemRarity.Magic)),
    ("rarity_matches", ["tributes"], TestTribute(name="tribute_of_ascendance_resolute", rarity=ItemRarity.Unique)),
    ("not_in_list", [], TestTribute(name="tribute_of_fake")),
]
