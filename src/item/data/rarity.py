from enum import Enum


class ItemRarity(Enum):
    Common = "common"
    Legendary = "legendary"
    Magic = "magic"
    Mythic = "mythic"
    Rare = "rare"
    Unique = "unique"


def is_junk_rarity(item_rarity: ItemRarity) -> bool:
    return item_rarity in [ItemRarity.Common, ItemRarity.Magic, ItemRarity.Rare]
