from src.item.data.rarity import ItemRarity


def test_item_rarity_values_and_order():
    assert ItemRarity.Rare.value == "rare"
    assert ItemRarity.Mythic.value == "mythic"
    assert ItemRarity.Rare != ItemRarity.Mythic
