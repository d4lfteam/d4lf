from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.models import Item


class TestItem(Item):
    def __init__(self, rarity=ItemRarity.Legendary, power=910, is_codex_upgrade=True, **kwargs):
        super().__init__(rarity=rarity, power=power, codex_upgrade=is_codex_upgrade, item_type=ItemType.Helm, **kwargs)


aspects = [
    ("codex upgrade no profile", ["AspectUpgrades"], TestItem(aspect=Aspect(name="no_profile_aspect"))),
    ("no codex no profile", [], TestItem(aspect=Aspect(name="no_profile_aspect"), is_codex_upgrade=False)),
    (
        "codex upgrade match profile",
        ["aspect_profile.AspectUpgrades"],
        TestItem(aspect=Aspect(name="accelerating")),
    ),
]
