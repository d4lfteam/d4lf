"""Build normalization for the d2core source workflow."""

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING

from src.importing.d2core.equipment import normalize_variant
from src.importing.d2core.errors import (
    EQUIPMENT_CATALOG,
    NO_USABLE_VARIANT,
    OPTIONAL_NO_OUTPUT,
    UNUSABLE_VARIANT,
    D2CoreCatalogError,
    D2CoreImportError,
)
from src.importing.d2core.optional import has_talisman_category, normalize_talismans
from src.importing.d2core.paragon import normalize_paragon
from src.importing.d2core.source.helpers import class_name, has_type, select_variant_name
from src.importing.d2core.source.workflow import load_optional_catalog
from src.importing.pipeline import ExtractedBuild

if TYPE_CHECKING:
    from src.importing.contracts import ImportRequest
    from src.importing.d2core.catalog import CatalogStore
    from src.type_aliases import JsonValue

Warn = Callable[[str, str, str, str], None]


def normalize_build(
    raw_build: Mapping[str, JsonValue],
    selected: list[tuple[int, Mapping[str, JsonValue]]],
    request: ImportRequest,
    catalogs: CatalogStore,
    *,
    source_name: str,
    ensure_open: Callable[[], None],
    warn: Warn,
    set_variant: Callable[[str], None],
) -> ExtractedBuild:
    ensure_open()
    try:
        catalogs.require("affix")
        if has_type(selected, "uniqueitem"):
            catalogs.require("uniqueItem")
        ensure_open()
    except D2CoreCatalogError as error:
        raise D2CoreImportError(EQUIPMENT_CATALOG, error.detail, context=error.context) from error
    aspect_selected = [item for item in selected if _has_base_aspect_attempt(item[1])]
    talisman_selected = [
        item
        for item in selected
        if (request.options.import_charms and has_talisman_category(item[1], "charm"))
        or (request.options.import_seals and has_talisman_category(item[1], "seal"))
    ]
    paragon_selected = [
        item for item in selected if isinstance(item[1].get("paragon"), Mapping) and item[1].get("paragon")
    ]
    aspect_enabled = load_optional_catalog(
        catalogs, "aspect", bool(aspect_selected) and request.options.import_aspect_upgrades, aspect_selected, warn
    )
    talisman_enabled = load_optional_catalog(catalogs, "talisman", bool(talisman_selected), talisman_selected, warn)
    paragon_enabled = load_optional_catalog(
        catalogs, "paragon", bool(paragon_selected) and request.options.export_paragon, paragon_selected, warn
    )
    normalized_class_name = class_name(raw_build.get("char"))
    normalized = []
    for index, raw_variant in selected:
        ensure_open()
        set_variant(str(index))
        name = select_variant_name(raw_variant, index)
        variant = normalize_variant(
            raw_variant,
            variant_name=name,
            class_name=normalized_class_name,
            catalogs=catalogs,
            import_greater_affixes=request.options.import_greater_affixes,
            require_greater_affixes=request.options.require_greater_affixes,
            import_aspect_upgrades=aspect_enabled,
            warn=warn,
        )
        if aspect_enabled and _has_base_aspect_attempt(raw_variant) and not variant.aspect_upgrade_filters:
            warn(OPTIONAL_NO_OUTPUT, name, "aspect", "")
        if talisman_enabled:
            charm_filters, seal_filters = normalize_talismans(
                raw_variant,
                variant_name=name,
                catalogs=catalogs,
                import_greater_affixes=request.options.import_greater_affixes,
                require_greater_affixes=request.options.require_greater_affixes,
                import_charms=request.options.import_charms,
                import_seals=request.options.import_seals,
                warn=warn,
            )
            variant.charm_filters = charm_filters
            variant.seal_filters = seal_filters
            if request.options.import_charms and has_talisman_category(raw_variant, "charm") and not charm_filters:
                warn(OPTIONAL_NO_OUTPUT, name, "charm", "")
            if request.options.import_seals and has_talisman_category(raw_variant, "seal") and not seal_filters:
                warn(OPTIONAL_NO_OUTPUT, name, "seal", "")
        if paragon_enabled:
            paragon_steps = normalize_paragon(
                raw_variant, class_name=normalized_class_name, variant_name=name, catalogs=catalogs, warn=warn
            )
            if not paragon_steps:
                warn(OPTIONAL_NO_OUTPUT, name, "paragon", "")
            else:
                variant.paragon_steps = paragon_steps
        if not variant.affix_filters:
            warn(UNUSABLE_VARIANT, name, "equipment", "")
            continue
        normalized.append(variant)
    if not normalized:
        raise D2CoreImportError(NO_USABLE_VARIANT, "None of the selected d2core Variants had usable equipment")
    return ExtractedBuild(
        source_name=source_name,
        class_name=normalized_class_name,
        build_header=str(raw_build.get("title", "") or ""),
        season_number=str(raw_build.get("season", "") or ""),
        variants=normalized,
    )


def _has_base_aspect_attempt(raw_variant: Mapping[str, JsonValue]) -> bool:
    gear = raw_variant.get("gear")
    if not isinstance(gear, Mapping):
        return False
    return any(
        isinstance(item, Mapping)
        and str(item.get("type", "")).casefold() == "legendary"
        and bool(item.get("key"))
        and not any(item.get(field) for field in ("transfiguredAspect", "transfiguredAspectName"))
        for item in gear.values()
    )
