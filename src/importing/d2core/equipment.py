"""Catalog-backed equipment normalization for one d2core Variant."""

import re
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, cast

from src.game_data import WEAPON_TYPES, GameCatalog, ItemType
from src.importing.d2core.catalog import canonical_affix_name, canonical_catalog_name
from src.importing.d2core.errors import EQUIPMENT_JOIN, OPTIONAL_ENTRY_JOIN
from src.importing.filters import (
    create_item_affix_pool,
    fix_offhand_type,
    fix_weapon_type,
    update_mingreateraffixcount,
    weapon_slot_name_hint,
)
from src.importing.pipeline import Variant
from src.item import Affix, AffixType
from src.profiles import AspectUniqueFilterModel, ItemFilterModel

if TYPE_CHECKING:
    from src.importing.d2core.catalog import CatalogStore


Warn = Callable[[str, str, str, str], None]

SLOT_TYPES = {
    "0": ItemType.Helm,
    "1": ItemType.ChestArmor,
    "2": ItemType.Gloves,
    "3": ItemType.Legs,
    "4": ItemType.Boots,
    "8": ItemType.Amulet,
    "9": ItemType.Ring,
    "10": ItemType.Ring,
}
TYPE_ALIASES = {
    "helmet": ItemType.Helm,
    "chest": ItemType.ChestArmor,
    "chestarmor": ItemType.ChestArmor,
    "glove": ItemType.Gloves,
    "pants": ItemType.Legs,
    "legs": ItemType.Legs,
    "boot": ItemType.Boots,
    "amulet": ItemType.Amulet,
    "ring": ItemType.Ring,
    "weapon": None,
    "2hweapon": None,
    "offhand": None,
}


def normalize_variant(
    raw_variant: Mapping[str, object],
    *,
    variant_name: str,
    class_name: str,
    catalogs: CatalogStore,
    import_greater_affixes: bool,
    require_greater_affixes: bool,
    import_aspect_upgrades: bool,
    warn: Warn,
) -> Variant:
    """Translate required equipment and the independently optional aspect module."""
    affix_value = catalogs.require("affix").get("affix", {})
    unique_value = catalogs.data.get("uniqueItem", {}).get("uniqueItem", {})
    aspect_value = catalogs.data.get("aspect", {}).get("aspect", {})
    affix_catalog = cast("Mapping[str, object]", affix_value) if isinstance(affix_value, Mapping) else {}
    unique_catalog = cast("Mapping[str, object]", unique_value) if isinstance(unique_value, Mapping) else {}
    aspect_catalog = cast("Mapping[str, object]", aspect_value) if isinstance(aspect_value, Mapping) else {}
    filters: list[ItemFilterModel] = []
    hints: list[str | None] = []
    aspect_upgrades: list[str] = []
    gear = raw_variant.get("gear")
    if isinstance(gear, Mapping):
        for slot, raw_item in gear.items():
            if not isinstance(raw_item, Mapping):
                continue
            source_item = cast("Mapping[str, object]", raw_item)
            item_filter, hint = _normalize_item(
                source_item,
                slot=str(slot),
                class_name=class_name,
                affixes=affix_catalog,
                uniques=unique_catalog,
                import_greater_affixes=import_greater_affixes,
                require_greater_affixes=require_greater_affixes,
                warn=warn,
                variant_name=variant_name,
            )
            if item_filter is None:
                continue
            filters.append(item_filter)
            hints.append(hint)
            if (
                import_aspect_upgrades
                and str(raw_item.get("type", "")).casefold() == "legendary"
                and not any(raw_item.get(field) for field in ("transfiguredAspect", "transfiguredAspectName"))
            ):
                aspect_key = raw_item.get("key")
                aspect = _catalog_record(aspect_catalog, aspect_key)
                aspect_name = _canonical_aspect_name(aspect)
                if aspect_name and aspect_name not in aspect_upgrades:
                    aspect_upgrades.append(aspect_name)
                elif aspect_key:
                    warn(OPTIONAL_ENTRY_JOIN, variant_name, "aspect", str(aspect_key))
    return Variant(
        name=variant_name,
        affix_filters=filters,
        affix_filter_name_hints=hints,
        aspect_upgrade_filters=aspect_upgrades,
        paragon_build_name=variant_name,
    )


def _normalize_item(
    item: Mapping[str, object],
    *,
    slot: str,
    class_name: str,
    affixes: Mapping[str, object],
    uniques: Mapping[str, object],
    import_greater_affixes: bool,
    require_greater_affixes: bool,
    warn: Warn,
    variant_name: str,
) -> tuple[ItemFilterModel | None, str | None]:
    payload_item_type = str(item.get("itemType", ""))
    unique_like = str(item.get("type", "")).casefold() == "uniqueitem"
    unique_name = None
    unique_record: Mapping[str, object] | None = None
    if unique_like:
        unique_record = _catalog_record(uniques, item.get("key"))
        if unique_record is None:
            warn(EQUIPMENT_JOIN, variant_name, "equipment", str(item.get("key", "unknown")))
            return None, None
        unique_name = canonical_catalog_name(unique_record, GameCatalog().aspect_unique_dict)
        if not unique_name:
            warn(EQUIPMENT_JOIN, variant_name, "equipment", str(item.get("key", "unknown")))
            return None, None
    # Unique/Mythic types come from the joined catalog; non-Unique itemType is the stable base discriminator.
    item_type_text = _catalog_item_type(unique_record or {}) if unique_like else payload_item_type

    item_type = _item_type(item_type_text, slot=slot, class_name=class_name)
    if item_type is None:
        warn(EQUIPMENT_JOIN, variant_name, "equipment", slot)
        return None, None
    normalized_affixes: list[Affix] = []
    mods = item.get("mods", [])
    if isinstance(mods, list):
        for mod in mods:
            if not isinstance(mod, Mapping):
                continue
            key = str(mod.get("name", ""))
            record = _catalog_record(affixes, mod.get("name"))
            name = canonical_affix_name(record, GameCatalog().affix_dict)
            if not name:
                warn(EQUIPMENT_JOIN, variant_name, "equipment", key or "unknown")
                continue
            normalized_affixes.append(
                Affix(
                    name=name,
                    type=AffixType.greater
                    if import_greater_affixes and mod.get("greater") is True
                    else AffixType.normal,
                )
            )
    item_types = item_type if isinstance(item_type, list) else [item_type]
    item_filter = ItemFilterModel(item_type=item_types, min_power=100)
    if unique_name:
        item_filter.unique_aspect = [AspectUniqueFilterModel(name=unique_name)]
    if normalized_affixes:
        item_filter.affix_pool = create_item_affix_pool(normalized_affixes, unique_like=unique_like)
        update_mingreateraffixcount(item_filter, require_greater_affixes)
    hint = weapon_slot_name_hint(item_filter, slot)
    return item_filter, hint


def _item_type(raw: str, *, slot: str, class_name: str) -> ItemType | list[ItemType] | None:
    normalized = re.sub(r"[\s_\-]+", "", raw.casefold())
    if normalized in TYPE_ALIASES:
        result = TYPE_ALIASES[normalized]
        if result is not None:
            return result
        if "offhand" in normalized:
            return fix_offhand_type(raw, class_name)
        return WEAPON_TYPES if slot == "5" else None
    if raw:
        for item_type in ItemType:
            if (
                normalized == re.sub(r"[\s_\-]+", "", str(item_type.value).casefold())
                or normalized == item_type.name.casefold()
            ):
                return item_type
        if weapon := fix_weapon_type(raw):
            return weapon
    if slot in SLOT_TYPES:
        return SLOT_TYPES[slot]
    if slot == "5":
        return WEAPON_TYPES
    if slot == "12":
        return fix_offhand_type("offhand", class_name)
    return WEAPON_TYPES if slot in {"6", "7"} else None


def _catalog_record(catalog: Mapping[str, object], key: object) -> Mapping[str, object] | None:
    if key is None:
        return None
    value = catalog.get(str(key))
    if not isinstance(value, Mapping):
        return None
    return cast("Mapping[str, object]", value)


def _canonical_aspect_name(record: Mapping[str, object] | None) -> str | None:
    if record is None:
        return None
    aspect_mapping = {str(name): str(name) for name in GameCatalog().aspect_list}
    return canonical_catalog_name(record, aspect_mapping)


def _catalog_item_type(record: Mapping[str, object]) -> str:
    """Use the joined Unique/Mythic catalog type, never the payload display label."""
    for field in ("equipTypeName", "equipType"):
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return ""
