from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.models import Item


class TestTribute(Item):
    def __init__(self, rarity=ItemRarity.Common, item_type=ItemType.Tribute, **kwargs):
        super().__init__(rarity=rarity, item_type=item_type, **kwargs)


# Filter used: name=[andariel, harmony], rarity=[legendary]
# A tribute is kept when its name OR its rarity matches.
tributes = [
    # name matches, rarity does not → kept by name
    ("name_match_rarity_does_not", ["tributes"], TestTribute(name="tribute_of_andariel", rarity=ItemRarity.Magic)),
    # rarity matches, name does not → kept by rarity
    (
        "rarity_match_name_does_not",
        ["tributes"],
        TestTribute(name="tribute_of_ascendance_resolute", rarity=ItemRarity.Legendary),
    ),
    # both match → kept
    ("name_and_rarity_both_match", ["tributes"], TestTribute(name="tribute_of_harmony", rarity=ItemRarity.Legendary)),
    # neither matches → not kept
    ("neither_matches", [], TestTribute(name="tribute_of_ascendance_resolute", rarity=ItemRarity.Magic)),
    # name matches and item is mythic → kept by name (mythic fallback not needed)
    ("name_match_mythic", ["tributes"], TestTribute(name="tribute_of_andariel", rarity=ItemRarity.Mythic)),
    # neither matches but mythic → kept by mythic fallback
    ("mythic_fallback", ["Mythic Tribute"], TestTribute(name="tribute_of_fake", rarity=ItemRarity.Mythic)),
    # neither matches, not mythic → not kept
    ("not_in_list", [], TestTribute(name="tribute_of_fake")),
]
