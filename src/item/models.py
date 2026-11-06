from dataclasses import dataclass, field
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from src.game_data import ItemRarity, ItemType
    from src.item.data.affix import Affix
    from src.item.data.aspect import Aspect
    from src.item.data.seasonal_attribute import SeasonalAttribute


@dataclass
class Item:
    __hash__ = None

    affixes: list[Affix] = field(default_factory=list)
    aspect: Aspect | None = None
    codex_upgrade: bool = False
    cosmetic_upgrade: bool = False
    inherent: list[Affix] = field(default_factory=list)
    is_ancestral: bool = False
    is_in_shop: bool = False
    item_type: ItemType | None = None
    name: str | None = None
    original_name: str | None = None
    power: int | None = None
    rarity: ItemRarity | None = None
    seasonal_attribute: SeasonalAttribute | None = None
    set: str | None = None

    @override
    def __eq__(self, other: object) -> bool:
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
        if self.is_ancestral != other.is_ancestral:
            res = False
        if self.is_in_shop != other.is_in_shop:
            res = False
        if self.seasonal_attribute != other.seasonal_attribute:
            res = False
        if self.set != other.set:
            res = False
        return res


@dataclass
class MatchedFilter:
    profile: str
    matched_affixes: list[Affix] = field(default_factory=list)
    aspect_match: bool = False
    set_match: bool = False
    missing_affixes: list[str] = field(default_factory=list)


@dataclass
class FilterResult:
    keep: bool
    matched: list[MatchedFilter]
    skipped: bool = False
