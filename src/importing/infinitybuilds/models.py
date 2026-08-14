"""Private typed values shared by InfinityBuilds modules."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict, TypeVar

if TYPE_CHECKING:
    from src.type_aliases import JsonObject


class _RawAffix(TypedDict, total=False):
    affixId: str
    tempered: bool
    swapped: bool
    greater: bool
    value: int | float


class _GearPiece(TypedDict, total=False):
    kind: str
    itemId: str
    aspectId: str
    slot: str
    affixes: list[_RawAffix]


class _VariantData(TypedDict, total=False):
    id: str
    name: str
    gear: list[_GearPiece]
    paragon: JsonObject
    talisman: list[_GearPiece]


class BuildData(TypedDict):
    classId: str
    variants: list[_VariantData]


class _ValueRange(TypedDict, total=False):
    max: int | float


class _CatalogItem(TypedDict, total=False):
    id: str
    sourceId: str
    label: str
    rarity: str
    slot: str


class _CatalogAspect(TypedDict, total=False):
    id: str
    label: str


class _CatalogAffix(TypedDict, total=False):
    id: str
    label: str
    greaterAffixEligible: bool
    valueRange: _ValueRange


CatalogT = TypeVar("CatalogT", _CatalogItem, _CatalogAspect, _CatalogAffix)


@dataclass
class _ResolvedGearData:
    items: dict[str, _CatalogItem]
    aspects: dict[str, _CatalogAspect]
    affixes: dict[str, _CatalogAffix]
