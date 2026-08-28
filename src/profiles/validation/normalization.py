from typing import TYPE_CHECKING

from src.game_data import GameCatalog, ItemRarity
from src.perception import correct_name

if TYPE_CHECKING:
    from src.profiles.affixes import AffixFilterCountModel
    from src.type_aliases import YamlValue


def _parse_item_type_or_rarities(data: str | list[str]) -> list[str]:
    values = [data] if isinstance(data, str) else data
    catalog = GameCatalog()
    return [
        item_type.value if isinstance(value, str) and (item_type := catalog.item_type_from_text(value)) else value
        for value in values
    ]


def _validate_set_name(name: str | None, field_name: str) -> str | None:
    if not name:
        return None

    name = correct_name(name)
    if name not in GameCatalog().set_list:
        msg = f"{field_name} {name} does not exist"
        raise ValueError(msg)
    return name


def _normalize_rarities(data: str | list[str] | list[ItemRarity]) -> list[str]:
    values = [data] if isinstance(data, str) else data
    values = [v.value if isinstance(v, ItemRarity) else v for v in values]
    return [v.lower() if isinstance(v, str) else v for v in values]


def _normalize_tribute_names(data: str | list[str] | None) -> list[str]:
    if data is None:
        return []
    values = [data] if isinstance(data, str) else data

    tribute_dict = GameCatalog().tribute_dict
    normalized_names: list[str] = []
    for name in values:
        if not name:
            continue
        name_with_tribute = f"tribute_of_{name}"
        if name in tribute_dict:
            normalized_names.append(name)
            continue
        if name_with_tribute in tribute_dict:
            normalized_names.append(name_with_tribute)
            continue
        msg = f"No tribute named {name} or {name_with_tribute} exists"
        raise ValueError(msg)
    return normalized_names


def _as_string_keyed_dict(data: YamlValue) -> dict[str, YamlValue] | None:
    if not isinstance(data, dict):
        return None

    normalized: dict[str, YamlValue] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            return None
        normalized[key] = value
    return normalized


def _legacy_filter_values(value: YamlValue) -> list[YamlValue]:
    if isinstance(value, str) or value is None:
        return [value]
    if isinstance(value, list):
        return list(value)
    return [value]


def _validate_affix_pool_names(
    affix_pool: list[AffixFilterCountModel], valid_affixes: dict[str, str], field_name: str
) -> None:
    invalid_affix_names = sorted({
        affix.name for affix_group in affix_pool for affix in affix_group.count if affix.name not in valid_affixes
    })
    if invalid_affix_names:
        msg = f"{field_name} affix {', '.join(invalid_affix_names)} does not exist"
        raise ValueError(msg)
