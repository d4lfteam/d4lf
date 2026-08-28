"""Small pure helpers used by the d2core source workflow."""

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, cast

from src.importing.d2core.errors import SCHEMA_DRIFT, D2CoreImportError
from src.importing.filters import PLAYER_CLASSES

if TYPE_CHECKING:
    from src.type_aliases import JsonValue


def select_variant_name(value: JsonValue, index: int) -> str:
    name = value.get("name") if isinstance(value, Mapping) else ""
    return str(name).strip() or f"Variant {index}"


def class_name(value: JsonValue) -> str:
    raw = str(value or "")
    lowered = raw.casefold()
    for known_class in PLAYER_CLASSES:
        if known_class in lowered:
            return known_class.title()
    return "Unknown"


def has_type(selected: list[tuple[int, Mapping[str, JsonValue]]], item_type: str) -> bool:
    return any(
        isinstance(item, Mapping) and str(item.get("type", "")).casefold() == item_type
        for _, variant in selected
        for item in (
            cast("Mapping[str, JsonValue]", variant["gear"]).values()
            if isinstance(variant.get("gear"), Mapping)
            else []
        )
    )


def decode_body(value: str | Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    parsed: JsonValue = value
    if isinstance(value, str):
        try:
            parsed = cast("JsonValue", json.loads(value))
        except json.JSONDecodeError as error:
            raise D2CoreImportError(SCHEMA_DRIFT, "The d2core response body was not valid JSON") from error
    if not isinstance(parsed, Mapping):
        raise D2CoreImportError(SCHEMA_DRIFT, "The d2core response body was not an object")
    return cast("Mapping[str, JsonValue]", parsed)
