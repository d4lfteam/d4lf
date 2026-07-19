from src.importing.mobalytics.filters import _resolve_item_type


def test_mobalytics_filter_type_resolution_handles_missing_values() -> None:
    assert _resolve_item_type([], "", "") is None
