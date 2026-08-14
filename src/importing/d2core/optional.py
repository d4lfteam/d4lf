"""Best-effort d2core Charm and Seal normalization."""

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, cast

from src.game_data import GameCatalog, ItemRarity
from src.importing.d2core.catalog import canonical_affix_name, canonical_catalog_name
from src.importing.d2core.errors import OPTIONAL_ENTRY_JOIN, OPTIONAL_NO_OUTPUT
from src.importing.filters import create_seal_charm_filter
from src.item import Affix, AffixType
from src.perception import correct_name
from src.profiles import CharmFilterModel, SealFilterModel

if TYPE_CHECKING:
    from src.importing.d2core.catalog import CatalogStore
    from src.type_aliases import JsonValue

Warn = Callable[[str, str, str, str], None]


def has_talisman_category(raw_variant: Mapping[str, JsonValue], category: str) -> bool:
    entries = raw_variant.get("charms")
    if not isinstance(entries, list):
        return False
    for entry in entries:
        if not isinstance(entry, Mapping) or not entry:
            continue
        source_type = str(entry.get("type", "")).casefold()
        if category == "seal" and source_type in {"horadricseal", "seal"}:
            return True
        if category == "charm" and source_type in {"charm", "horadriccharm"}:
            return True
    return False


def normalize_talismans(
    raw_variant: Mapping[str, JsonValue],
    *,
    variant_name: str,
    catalogs: CatalogStore,
    import_greater_affixes: bool,
    require_greater_affixes: bool,
    import_charms: bool,
    import_seals: bool,
    warn: Warn,
) -> tuple[list[CharmFilterModel], list[SealFilterModel]]:
    charm_filters: list[CharmFilterModel] = []
    seal_filters: list[SealFilterModel] = []
    catalog = catalogs.data.get("talisman", {})
    raw_entries = raw_variant.get("charms")
    raw_entry_list = raw_entries if isinstance(raw_entries, list) else []
    for raw_entry in raw_entry_list:
        if not isinstance(raw_entry, Mapping) or not raw_entry:
            continue
        source_entry = cast("Mapping[str, JsonValue]", raw_entry)
        source_type = str(source_entry.get("type", "")).casefold()
        if source_type in {"charm", "horadriccharm"}:
            is_seal = False
        elif source_type in {"horadricseal", "seal"}:
            is_seal = True
        else:
            warn(OPTIONAL_ENTRY_JOIN, variant_name, "talisman", source_type)
            continue
        category = "seal" if is_seal else "charm"
        if (is_seal and not import_seals) or (not is_seal and not import_charms):
            continue
        category_entries = catalog.get(category, {})
        record = category_entries.get(str(source_entry.get("key"))) if isinstance(category_entries, Mapping) else None
        if not isinstance(record, Mapping):
            warn(OPTIONAL_ENTRY_JOIN, variant_name, category, str(source_entry.get("key", "unknown")))
            continue
        quality = str(source_entry.get("itemQuality", record.get("quality", ""))).casefold()
        set_key = source_entry.get("set") or record.get("set")
        if category == "charm" and set_key and quality in {"unique", "mythic"}:
            warn(OPTIONAL_ENTRY_JOIN, variant_name, category, str(source_entry.get("key", "unknown")))
            continue
        filter_model = _normalize_talisman(
            source_entry,
            record=cast("Mapping[str, JsonValue]", record),
            category=category,
            catalog=catalog,
            variant_name=variant_name,
            import_greater_affixes=import_greater_affixes,
            require_greater_affixes=require_greater_affixes,
            warn=warn,
        )
        if filter_model is None:
            warn(OPTIONAL_NO_OUTPUT, variant_name, category, str(source_entry.get("key", "unknown")))
        elif is_seal:
            seal_filters.append(cast("SealFilterModel", filter_model))
        else:
            charm_filters.append(cast("CharmFilterModel", filter_model))
    return charm_filters, seal_filters


def _normalize_talisman(
    raw_entry: Mapping[str, JsonValue],
    *,
    record: Mapping[str, JsonValue],
    category: str,
    catalog: Mapping[str, JsonValue],
    variant_name: str,
    import_greater_affixes: bool,
    require_greater_affixes: bool,
    warn: Warn,
) -> CharmFilterModel | SealFilterModel | None:
    unique_name = None
    quality = str(raw_entry.get("itemQuality", record.get("quality", ""))).casefold()
    if quality in {"unique", "mythic"}:
        unique_name = _canonical_unique(str(record.get("name", record.get("engName", ""))))
    set_name = None
    set_key = raw_entry.get("set") or record.get("set")
    if category == "charm" and set_key:
        sets = catalog.get("itemSets", {})
        set_record = sets.get(str(set_key)) if isinstance(sets, Mapping) else None
        if isinstance(set_record, Mapping):
            set_name = _canonical_set(str(set_record.get("name", set_record.get("engName", ""))))
        else:
            warn(OPTIONAL_ENTRY_JOIN, variant_name, "charm", str(set_key))
    affix_records_value = catalog.get("affixes", {})
    affix_records = affix_records_value.get(category, {}) if isinstance(affix_records_value, Mapping) else {}
    affix_records = cast("Mapping[str, JsonValue]", affix_records) if isinstance(affix_records, Mapping) else {}
    affixes: list[Affix] = []
    raw_mods = raw_entry.get("mods", [])
    if isinstance(raw_mods, list):
        for raw_mod in raw_mods:
            if not isinstance(raw_mod, Mapping):
                continue
            key = str(raw_mod.get("name", ""))
            raw_record = affix_records.get(key)
            record: Mapping[str, JsonValue] | None = (
                cast("Mapping[str, JsonValue]", raw_record) if isinstance(raw_record, Mapping) else None
            )
            mapping = GameCatalog().seal_affix_dict if category == "seal" else GameCatalog().charm_affix_dict
            name = canonical_affix_name(record, mapping)
            if not name:
                warn(OPTIONAL_ENTRY_JOIN, variant_name, category, key or "unknown")
                continue
            affixes.append(
                Affix(
                    name=name,
                    type=AffixType.greater
                    if import_greater_affixes and raw_mod.get("greater") is True
                    else AffixType.normal,
                )
            )
    if not affixes and not unique_name and not set_name:
        return None
    if category == "seal":
        result = create_seal_charm_filter(
            affixes=affixes,
            require_gas=require_greater_affixes,
            model_type=SealFilterModel,
            unique_name=unique_name,
            set_name=set_name,
        )
    else:
        result = create_seal_charm_filter(
            affixes=affixes,
            require_gas=require_greater_affixes,
            model_type=CharmFilterModel,
            unique_name=unique_name,
            set_name=set_name,
        )
    rarity = _rarity(quality)
    if rarity is not None:
        result.rarities = [rarity]
    return result


def _canonical_unique(raw_name: str) -> str | None:
    return canonical_catalog_name({"name": raw_name}, GameCatalog().aspect_unique_dict)


def _canonical_set(raw_name: str) -> str | None:
    normalized = correct_name(raw_name) or ""
    return normalized if normalized in GameCatalog().set_list else None


def _rarity(raw: str) -> ItemRarity | None:
    return next((rarity for rarity in ItemRarity if rarity.value == raw or rarity.name.casefold() == raw), None)
