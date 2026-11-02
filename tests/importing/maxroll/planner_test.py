import json

import pytest

from src.game_data import ItemType
from src.importing import ImportSourceError
from src.importing.maxroll.constants import PLANNER_API_BASE_URL, PLANNER_BASE_URL
from src.importing.maxroll.planner import (
    MaxrollError,
    _normalize_item_type_str_for_import_helpers,
    extract_planner_url_and_id_from_planner,
    find_item_type,
    resolve_visible_profile_index,
)


def test_maxroll_errors_are_import_source_errors() -> None:
    assert issubclass(MaxrollError, ImportSourceError)


def test_maxroll_planner_normalizes_weapon_hands() -> None:
    assert _normalize_item_type_str_for_import_helpers("TwoHandedSword") == "two handed sword"


def test_maxroll_planner_nonnumeric_fragment_uses_active_profile(mocker) -> None:
    response = mocker.Mock()
    response.json.return_value = {"data": json.dumps({"activeProfile": 2})}
    get = mocker.patch("src.importing.maxroll.planner.get_with_retry", return_value=response)
    planner_url = f"{PLANNER_BASE_URL}test-profile#paperdoll=3,2,1"

    assert extract_planner_url_and_id_from_planner(planner_url) == (f"{PLANNER_API_BASE_URL}test-profile", 2, False)
    get.assert_called_once_with(url=f"{PLANNER_API_BASE_URL}test-profile")


def test_maxroll_planner_numeric_fragment_is_visible_position(mocker) -> None:
    planner_url = f"{PLANNER_BASE_URL}test-profile#3"

    assert extract_planner_url_and_id_from_planner(planner_url) == (f"{PLANNER_API_BASE_URL}test-profile", 2, True)


@pytest.mark.parametrize(
    ("type_name", "class_name", "expected"),
    [
        pytest.param("2H Sword", "Barbarian", ItemType.Sword2H, id="weapon-type-with-slot-context"),
        pytest.param("FocusBookOffHand", "Sorcerer", ItemType.Focus, id="offhand-type-with-slot-and-class-context"),
        pytest.param("1HFocus", "Sorcerer", ItemType.Focus, id="offhand-type-implied-by-item-type"),
    ],
)
def test_find_item_type_applies_maxroll_type_fixes(type_name: str, class_name: str, expected: ItemType) -> None:
    mapping_data = {"item-1": {"type": type_name}}
    assert find_item_type(mapping_data=mapping_data, value="item-1", class_name=class_name) == expected


def test_resolve_visible_profile_index_skips_hidden_profiles() -> None:
    profiles = [
        {"name": "Any hidden variant name", "hidden": True},
        {"name": "Visible variant A"},
        {"name": "Visible variant B"},
        {"name": "Visible variant C"},
    ]

    assert resolve_visible_profile_index(profiles=profiles, visible_profile_index=2) == 3
