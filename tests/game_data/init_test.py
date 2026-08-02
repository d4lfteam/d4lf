from src.game_data import GameCatalog, ItemRarity, ItemType


def test_game_data_facade_exports_catalog_and_shared_metadata():
    assert GameCatalog is not None
    assert ItemType.Helm.value == "helm"
    assert ItemRarity.Unique.value == "unique"
