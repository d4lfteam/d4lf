import logging
from enum import Enum
from typing import TYPE_CHECKING, TypeVar, overload

import rapidfuzz

from src.game_data import WEAPON_TYPES, GameCatalog, ItemRarity, ItemType
from src.item import Affix, AffixType
from src.perception import closest_match
from src.profiles import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    CharmFilterModel,
    ItemFilterModel,
    SealFilterModel,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


E = TypeVar("E", bound=Enum)
FilterModelT = TypeVar("FilterModelT", bound=ItemFilterModel | CharmFilterModel | SealFilterModel)
LOGGER = logging.getLogger(__name__)


def fix_weapon_type(input_str: str) -> ItemType | None:
    input_str = input_str.lower()
    weapon_types = {
        "1h axe": ItemType.Axe,
        "1h mace": ItemType.Mace,
        "1h sword": ItemType.Sword,
        "2h axe": ItemType.Axe2H,
        "2h mace": ItemType.Mace2H,
        "2h scythe": ItemType.Scythe2H,
        "2h sword": ItemType.Sword2H,
        "bow": ItemType.Bow,
        "crossbow": ItemType.Crossbow2H,
        "dagger": ItemType.Dagger,
        "flail": ItemType.Flail,
        "glaive": ItemType.Glaive,
        "polearm": ItemType.Polearm,
        "quarterstaff": ItemType.Quarterstaff,
        "scythe": ItemType.Scythe,
        "staff": ItemType.Staff,
        "wand": ItemType.Wand,
    }
    for name, item_type in weapon_types.items():
        if name in input_str:
            return item_type
    return None


def fix_offhand_type(input_str: str, class_str: str) -> ItemType | None:
    input_str, class_str = input_str.lower(), class_str.lower()
    if "sorc" in class_str or "warlock" in class_str:
        return ItemType.Focus
    if "druid" in class_str:
        return ItemType.OffHandTotem
    if "paladin" in class_str:
        return ItemType.Shield
    if "necro" in class_str:
        if "focus" in input_str:
            return ItemType.Focus
        if "shield" in input_str:
            return ItemType.Shield
    return None


PLAYER_CLASSES = ["barbarian", "druid", "necromancer", "rogue", "sorcerer", "spiritborn", "paladin", "warlock"]


def get_class_name(input_str: str) -> str:
    for class_name in PLAYER_CLASSES:
        if class_name in input_str.lower():
            return class_name.title()
    LOGGER.error(f"Couldn't match class name {input_str=}")
    return "Unknown"


def update_mingreateraffixcount(item_filter: ItemFilterModel, require_gas: bool) -> None:
    item_filter.min_greater_affix_count = (
        sum(affix.want_greater for affix in item_filter.affix_pool[0].count) if require_gas else 0
    )


def affix_dict_for_item_type(item_type: ItemType | None) -> dict[str, str]:
    if item_type == ItemType.HoradricSeal:
        return GameCatalog().seal_affix_dict
    if item_type == ItemType.Charm:
        return GameCatalog().charm_affix_dict
    return GameCatalog().affix_dict


def match_set_aware_seal_affix(stat_clean: str, affix_dict: dict[str, str], guessed_set_name: str) -> str | None:
    best_global_key = closest_match(stat_clean, affix_dict)
    if best_global_key and best_global_key != "damage":
        global_display = affix_dict[best_global_key]
        if rapidfuzz.distance.Levenshtein.distance(stat_clean, global_display) <= 2:
            is_set_specific = any(best_global_key.startswith(f"{set_name}_") for set_name in GameCatalog().set_list)
            if not is_set_specific:
                return best_global_key
    set_affixes = {
        key: value for key, value in GameCatalog().seal_affix_dict.items() if key.startswith(f"{guessed_set_name}_")
    }
    if not set_affixes:
        return None
    potential_match = closest_match(stat_clean, set_affixes)
    if potential_match is None:
        return None
    display_name = GameCatalog().seal_affix_dict[potential_match]
    return potential_match if rapidfuzz.fuzz.token_set_ratio(stat_clean, display_name) >= 50 else None


def is_unique_like_rarity(rarity: ItemRarity | str | None) -> bool:
    if isinstance(rarity, ItemRarity):
        return rarity in (ItemRarity.Unique, ItemRarity.Mythic)
    return str(rarity).strip().casefold() in {"unique", "mythic"}


def create_item_affix_pool(affixes: list[Affix], unique_like: bool) -> list[AffixFilterCountModel]:
    if not affixes:
        return []
    return [
        AffixFilterCountModel(
            count=[AffixFilterModel(name=a.name, want_greater=a.type == AffixType.greater) for a in affixes],
            min_count=1 if unique_like else 3,
        )
    ]


@overload
def create_seal_charm_filter(
    affixes: list[Affix],
    require_gas: bool,
    model_type: type[SealFilterModel] = SealFilterModel,
    unique_name: str | None = None,
    set_name: str | None = None,
) -> SealFilterModel: ...


@overload
def create_seal_charm_filter(
    affixes: list[Affix],
    require_gas: bool,
    model_type: type[CharmFilterModel],
    unique_name: str | None = None,
    set_name: str | None = None,
) -> CharmFilterModel: ...


@overload
def create_seal_charm_filter(
    affixes: list[Affix],
    require_gas: bool,
    model_type: type[SealFilterModel | CharmFilterModel],
    unique_name: str | None = None,
    set_name: str | None = None,
) -> SealFilterModel | CharmFilterModel: ...


def create_seal_charm_filter(
    affixes: list[Affix],
    require_gas: bool,
    model_type: type[SealFilterModel | CharmFilterModel] = SealFilterModel,
    unique_name: str | None = None,
    set_name: str | None = None,
) -> SealFilterModel | CharmFilterModel:
    affix_pool = (
        [
            AffixFilterCountModel(
                count=[AffixFilterModel(name=a.name, want_greater=a.type == AffixType.greater) for a in affixes],
                minCount=1,
            )
        ]
        if affixes
        else []
    )
    result = (
        CharmFilterModel(set=[set_name] if set_name else []) if model_type is CharmFilterModel else SealFilterModel()
    )
    result.affix_pool = affix_pool
    result.unique_aspect = [AspectUniqueFilterModel(name=unique_name)] if unique_name else []
    if require_gas:
        result.min_greater_affix_count = sum(a.type == AffixType.greater for a in affixes)
    return result


def weapon_slot_name_hint(item_filter: ItemFilterModel, slot: str) -> str | None:
    """Name hint kept only while the weapon's item type is still unresolved."""
    return slot if item_filter.item_type == WEAPON_TYPES else None


def unique_filter_name[FilterT](filter_name_template: str, filters: Sequence[Mapping[str, FilterT]]) -> str:
    filter_name, i = filter_name_template, 2
    while any(filter_name == next(iter(existing_filter)) for existing_filter in filters):
        filter_name, i = f"{filter_name_template}{i}", i + 1
    return filter_name


def deduplicate_filters(
    filters: Sequence[FilterModelT], name_hints: Sequence[str | None] | None = None
) -> list[dict[str, FilterModelT]]:
    """Merge identical filters, naming duplicates with an (xN) count suffix."""
    if not filters:
        return []
    groups: list[tuple[str, FilterModelT, int]] = []
    for i, filter_spec in enumerate(filters):
        for idx, (base_name, existing_model, count) in enumerate(groups):
            if filter_spec == existing_model:
                groups[idx] = (base_name, existing_model, count + 1)
                break
        else:
            if isinstance(filter_spec, ItemFilterModel):
                hint = name_hints[i] if name_hints else None
                base_name = (
                    hint
                    if hint and filter_spec.item_type == WEAPON_TYPES
                    else (filter_spec.item_type[0].name if filter_spec.item_type else "Item")
                )
            else:
                base_name = "Charm" if isinstance(filter_spec, CharmFilterModel) else "HoradricSeal"
            groups.append((base_name, filter_spec, 1))
    result: list[dict[str, FilterModelT]] = []
    used_names: list[dict[str, FilterModelT]] = []
    for base_name, model, count in groups:
        key = f"{base_name}(x{count})" if count > 1 else unique_filter_name(base_name, used_names)
        suffix = 2
        while count > 1 and any(key == next(iter(existing)) for existing in used_names):
            key, suffix = f"{base_name}{suffix}(x{count})", suffix + 1
        result.append({key: model})
        used_names.append({key: model})
    return result


def sort_profile_filters(filters: Sequence[Mapping[str, FilterModelT]]) -> list[dict[str, FilterModelT]]:
    return [dict(entry) for entry in sorted(filters, key=lambda entry: next(iter(entry)).casefold())]


def match_to_enum(enum_class: type[E], target_string: str, check_keys: bool = False) -> E | None:
    target_string = target_string.casefold().replace(" ", "").replace("-", "")
    for member in enum_class:
        if str(member.value).casefold().replace(" ", "").replace("-", "") == target_string or (
            check_keys and member.name.casefold().replace(" ", "").replace("-", "") == target_string
        ):
            return member
    return None
