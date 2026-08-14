"""Variant selection and optional catalog workflow for d2core imports."""

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, cast

from src.importing.d2core.errors import (
    OPTIONAL_CATALOG,
    SCHEMA_DRIFT,
    UNKNOWN_SELECTION,
    D2CoreCatalogError,
    D2CoreImportError,
)

if TYPE_CHECKING:
    from src.importing.contracts import ImportRequest
    from src.importing.d2core.catalog import CatalogStore
    from src.type_aliases import JsonValue

Warn = Callable[[str, str, str, str], None]


def resolve_variants(
    variants: JsonValue, planner_variant: int | None, request: ImportRequest, warn: Warn
) -> list[tuple[int, Mapping[str, JsonValue]]]:
    if not isinstance(variants, list):
        raise D2CoreImportError(SCHEMA_DRIFT, "The d2core Variant list was malformed")
    available = [
        (index, cast("Mapping[str, JsonValue]", value))
        for index, value in enumerate(variants, start=1)
        if isinstance(value, Mapping)
    ]
    if request.options.multi_build:
        wanted = None if request.variant_selection is None else tuple(request.variant_selection.ids)
        if wanted is None:
            return available
        wanted_set = set(wanted)
        for value in wanted_set - {str(index) for index, _ in available}:
            warn(UNKNOWN_SELECTION, "", "selection", value)
        return [(index, value) for index, value in available if str(index) in wanted_set]
    selected_index = planner_variant if planner_variant in {index for index, _ in available} else 1
    return [(index, value) for index, value in available if index == selected_index]


def load_optional_catalog(
    catalogs: CatalogStore, kind: str, enabled: bool, selected: list[tuple[int, Mapping[str, JsonValue]]], warn: Warn
) -> bool:
    if not enabled:
        return False
    try:
        catalogs.optional(kind)
    except D2CoreCatalogError:
        for index, raw_variant in selected:
            name = str(raw_variant.get("name", "")).strip() or f"Variant {index}"
            warn(OPTIONAL_CATALOG, f"{index}:{name}", kind, "")
        return False
    return True
