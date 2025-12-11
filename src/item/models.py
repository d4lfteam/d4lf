import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.item.data.affix import Affix
    from src.item.data.aspect import Aspect
    from src.item.data.item_type import ItemType
    from src.item.data.rarity import ItemRarity

LOGGER = logging.getLogger(__name__)


@dataclass
class Item:
    affixes: list[Affix] = field(default_factory=list)
    aspect: Aspect | None = None
    codex_upgrade: bool = False
    cosmetic_upgrade: bool = False
    inherent: list[Affix] = field(default_factory=list)
    is_chaos: bool = False
    is_in_shop: bool = False
    item_type: ItemType | None = None
    name: str | None = None
    power: int | None = None
    rarity: ItemRarity | None = None
    sanctified: bool = False

    def __eq__(self, other):
        if not isinstance(other, Item):
            return False
        res = True
        if self.affixes != other.affixes:
            # LOGGER.debug("Affixes do not match")
            res = False
        if self.aspect != other.aspect:
            # LOGGER.debug("Aspect not the same")
            res = False
        if self.codex_upgrade != other.codex_upgrade:
            # LOGGER.debug("Codex upgrade not the same")
            res = False
        if self.cosmetic_upgrade != other.cosmetic_upgrade:
            # LOGGER.debug("Cosmetic upgrade not the same")
            res = False
        if self.inherent != other.inherent:
            # LOGGER.debug("Inherent affixes do not match")
            res = False
        if self.item_type != other.item_type:
            # LOGGER.debug("Type not the same")
            res = False
        if self.power != other.power:
            # LOGGER.debug("Power not the same")
            res = False
        if self.name != other.name:
            # LOGGER.debug("Names do not match")
            res = False
        if self.rarity != other.rarity:
            # LOGGER.debug("Rarity not the same")
            res = False
        if self.is_in_shop != other.is_in_shop:
            res = False
        if self.is_chaos != other.is_chaos:
            res = False
        return res


class ItemJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Item):
            return {
                "affixes": [affix.__dict__ for affix in o.affixes],
                "aspect": o.aspect.__dict__ if o.aspect else None,
                "codex_upgrade": o.codex_upgrade,
                "cosmetic_upgrade": o.cosmetic_upgrade,
                "inherent": [affix.__dict__ for affix in o.inherent],
                "item_type": o.item_type.value if o.item_type else None,
                "name": o.name if o.name else None,
                "power": o.power if o.power else None,
                "rarity": o.rarity.value if o.rarity else None,
            }
        return super().default(o)
