from collections.abc import Mapping


def as_string_keyed_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {key: item for key, item in value.items() if isinstance(key, str)}


def as_string_keyed_mapping_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [as_string_keyed_mapping(item) for item in value if isinstance(item, Mapping)]


def as_text(value: object) -> str:
    return value if isinstance(value, str) else ""
