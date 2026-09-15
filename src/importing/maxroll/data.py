from typing import TYPE_CHECKING

from src.type_aliases import JsonObject

if TYPE_CHECKING:
    from collections.abc import Mapping

type PlannerObject = JsonObject


def _find_item_name(
    *, resolved_item: PlannerObject, resolved_item_id: str, item_mapping: Mapping[str, PlannerObject]
) -> str | None:
    return next(
        (
            item_name
            for item_data in (item_mapping.get(resolved_item_id), resolved_item)
            if item_data is not None and isinstance(item_name := item_data.get("name"), str) and item_name.strip()
        ),
        None,
    )


def _merge_localized_data(mapping_data: JsonObject, localized_data: JsonObject) -> None:
    """Merge Maxroll's localized records into its structural game data."""
    for section, localized_section in localized_data.items():
        mapping_section = mapping_data.get(section)
        if not isinstance(mapping_section, dict) or not isinstance(localized_section, dict):
            continue
        for key, localized_entry in localized_section.items():
            mapping_entry = mapping_section.get(key)
            if isinstance(mapping_entry, dict) and isinstance(localized_entry, dict):
                mapping_entry.update(localized_entry)
            elif isinstance(localized_entry, str):
                mapping_section[key] = localized_entry
