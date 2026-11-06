from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.game_data import ItemRarity, ItemType
    from src.item.data.affix import Affix
    from src.item.data.aspect import Aspect
    from src.item.data.seasonal_attribute import SeasonalAttribute


@dataclass
class Item:
    affixes: list[Affix] = field(default_factory=list)
    aspect: Aspect | None = None
    codex_upgrade: bool = False
    cosmetic_upgrade: bool = False
    inherent: list[Affix] = field(default_factory=list)
    is_ancestral: bool = False
    is_in_shop: bool = False
    item_type: ItemType | None = None
    name: str | None = None
    original_name: str | None = field(default=None, compare=False)
    power: int | None = None
    rarity: ItemRarity | None = None
    seasonal_attribute: SeasonalAttribute | None = None
    set: str | None = None


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
