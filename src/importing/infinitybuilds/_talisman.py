"""Convert Infinity Builds talisman payloads into ordinary catalog gear inputs."""

from typing import TYPE_CHECKING, cast

from src.importing.conversion import as_string_keyed_mapping as _as_object
from src.item import Dataloader
from src.perception import correct_name

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.importing.infinitybuilds.models import _CatalogItem, _GearPiece, _RawAffix


def _parse_talisman_gear(value: object) -> list[_GearPiece]:
    raw = _as_object(value)
    gear: list[_GearPiece] = []
    seal = raw.get("seal")
    if isinstance(seal, str):
        gear.append({"kind": "talisman", "slot": "seal", "itemId": seal})
    charms = raw.get("charms")
    for index, charm_id in enumerate(charms if isinstance(charms, list) else []):
        if not isinstance(charm_id, str):
            continue
        gear.append({
            "kind": "talisman",
            "slot": f"charm{index + 1}",
            "itemId": charm_id,
            "affixes": _parse_charm_affixes(raw, index),
        })
    return gear


def _parse_charm_affixes(raw: dict[str, object], charm_index: int) -> list[_RawAffix]:
    result: list[_RawAffix] = []
    affix_ids = _nested_row(raw.get("charmAffixes"), charm_index)
    values = _nested_row(raw.get("charmAffixValues"), charm_index)
    greater_flags = _nested_row(raw.get("charmAffixGreater"), charm_index)
    for affix_index, affix_id in enumerate(affix_ids):
        if not isinstance(affix_id, str):
            continue
        affix: _RawAffix = {"affixId": affix_id}
        value = _optional_value_at(values, affix_index)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            affix["value"] = value
        if _optional_value_at(greater_flags, affix_index) is True:
            affix["greater"] = True
        result.append(affix)
    return result


def _catalog_items_by_id(items: Sequence[_CatalogItem]) -> dict[str, _CatalogItem]:
    result = {item["id"]: item for item in items if "id" in item}
    for item in items:
        source_id = item.get("sourceId")
        if source_id:
            result[source_id.removesuffix(".itm")] = item
    return result


def _charm_set_name(label: str) -> str | None:
    _, separator, suffix = label.partition(" of ")
    candidate = correct_name(suffix) if separator else None
    return candidate if candidate in Dataloader().set_list else None


def _nested_row(rows: object, index: int) -> list[object]:
    if not isinstance(rows, list) or index >= len(rows):
        return []
    row = rows[index]
    return cast("list[object]", row) if isinstance(row, list) else []


def _optional_value_at(row: list[object], index: int) -> object:
    return row[index] if index < len(row) else None
