import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast, override

if TYPE_CHECKING:
    from src.game_data import ItemRarity, ItemType
    from src.item.data.affix import Affix
    from src.item.data.aspect import Aspect
    from src.item.data.seasonal_attribute import SeasonalAttribute
    from src.type_aliases import JsonValue


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

    # ty: ignore[invalid-method-override, missing-override-decorator] - this project intentionally uses a same-type equality contract
    def __eq__(self, other: Item) -> bool:
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


@dataclass
class FilterResult:
    keep: bool
    matched: list[MatchedFilter]
    skipped: bool = False


class ItemJSONEncoder(json.JSONEncoder):
    @override
    def default(self, o: Item | JsonValue) -> JsonValue:
        if isinstance(o, Item):
            return {
                "affixes": [
                    {
                        "loc": affix.loc,
                        "max_value": affix.max_value,
                        "min_value": affix.min_value,
                        "name": affix.name,
                        "text": affix.text,
                        "type": affix.type.value,
                        "value": affix.value,
                    }
                    for affix in o.affixes
                ],
                "aspect": (
                    {
                        "name": o.aspect.name,
                        "loc": o.aspect.loc,
                        "min_value": o.aspect.min_value,
                        "max_value": o.aspect.max_value,
                        "text": o.aspect.text,
                        "value": o.aspect.value,
                    }
                    if o.aspect
                    else None
                ),
                "codex_upgrade": o.codex_upgrade,
                "cosmetic_upgrade": o.cosmetic_upgrade,
                "inherent": [
                    {
                        "loc": affix.loc,
                        "max_value": affix.max_value,
                        "min_value": affix.min_value,
                        "name": affix.name,
                        "text": affix.text,
                        "type": affix.type.value,
                        "value": affix.value,
                    }
                    for affix in o.inherent
                ],
                "is_ancestral": o.is_ancestral,
                "item_type": o.item_type.value if o.item_type else None,
                "name": o.name or None,
                "power": o.power or None,
                "rarity": o.rarity.value if o.rarity else None,
                "set_name": o.set or None,
            }
        return cast("JsonValue", super().default(o))
