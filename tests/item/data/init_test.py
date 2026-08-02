from src.game_data import ItemType
from src.item.data.affix import Affix


def test_data_package_exposes_item_values_through_owned_modules() -> None:
    assert Affix(name="armor").name == "armor"
    assert ItemType.Helm.value == "helm"
