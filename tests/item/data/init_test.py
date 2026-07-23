from src.item.data.affix import Affix
from src.item.data.item_type import ItemType


def test_data_package_exposes_item_values_through_owned_modules() -> None:
    assert Affix(name="armor").name == "armor"
    assert ItemType.Helm.value == "helm"
