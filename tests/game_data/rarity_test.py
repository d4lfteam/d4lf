from src.game_data import ItemRarity


def test_item_rarity_values_are_canonical():
    assert ItemRarity.Rare.value == "rare"
