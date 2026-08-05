"""Small pure helpers used by the d2core source workflow."""

import json
from collections.abc import Mapping
from typing import cast

from src.importing.d2core.errors import SCHEMA_DRIFT, D2CoreImportError
from src.importing.filters import PLAYER_CLASSES


def select_variant_name(value: object, index: int) -> str:
    name = value.get("name") if isinstance(value, Mapping) else ""
    return str(name).strip() or f"Variant {index}"


def class_name(value: object) -> str:
    raw = str(value or "")
    lowered = raw.casefold()
    for known_class in PLAYER_CLASSES:
        if known_class in lowered:
            return known_class.title()
    return "Unknown"


def has_type(selected: list[tuple[int, Mapping[str, object]]], item_type: str) -> bool:
    return any(
        isinstance(item, Mapping) and str(item.get("type", "")).casefold() == item_type
        for _, variant in selected
        for item in (
            cast("Mapping[str, object]", variant["gear"]).values() if isinstance(variant.get("gear"), Mapping) else []
        )
    )


def decode_body(value: object) -> Mapping[str, object]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise D2CoreImportError(SCHEMA_DRIFT, "The d2core response body was not valid JSON") from error
    if not isinstance(value, Mapping):
        raise D2CoreImportError(SCHEMA_DRIFT, "The d2core response body was not an object")
    return cast("Mapping[str, object]", value)
