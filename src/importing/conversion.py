from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.type_aliases import JsonObject, JsonValue


def as_string_keyed_mapping(value: JsonValue | Mapping[str | int, JsonValue] | None) -> JsonObject:
    if not isinstance(value, Mapping):
        return {}
    return {key: item for key, item in value.items() if isinstance(key, str)}


def as_string_keyed_mapping_list(value: JsonValue | Sequence[Mapping[str, JsonValue]]) -> list[JsonObject]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [as_string_keyed_mapping(item) for item in value if isinstance(item, Mapping)]


def as_text(value: JsonValue) -> str:
    return value if isinstance(value, str) else ""
