from src.importing.maxroll.planner import _normalize_item_type_str_for_import_helpers


def test_maxroll_planner_normalizes_weapon_hands() -> None:
    assert _normalize_item_type_str_for_import_helpers("TwoHandedSword") == "two handed sword"
