from typing import TYPE_CHECKING

from src.importing.maxroll.data import _find_item_name, _merge_localized_data

if TYPE_CHECKING:
    from src.type_aliases import JsonObject


def test_find_item_name_returns_none_when_both_records_are_unnamed() -> None:
    assert (
        _find_item_name(
            resolved_item={"id": "item-1"}, resolved_item_id="item-1", item_mapping={"item-1": {"type": "Helm"}}
        )
        is None
    )


def test_merge_localized_data_overlays_nested_records() -> None:
    mapping_data: JsonObject = {
        "items": {"item-1": {"type": "Helm", "magicType": 4}},
        "attributeDescriptions": {"old": "fallback"},
    }

    _merge_localized_data(
        mapping_data, {"items": {"item-1": {"name": "Harlequin Crest"}}, "attributeDescriptions": {"new": "localized"}}
    )

    assert mapping_data == {
        "items": {"item-1": {"type": "Helm", "magicType": 4, "name": "Harlequin Crest"}},
        "attributeDescriptions": {"old": "fallback", "new": "localized"},
    }
