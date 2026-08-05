import json

from src.importing import ImportSourceError
from src.importing.maxroll.constants import PLANNER_API_BASE_URL, PLANNER_BASE_URL
from src.importing.maxroll.planner import (
    MaxrollError,
    _extract_planner_url_and_id_from_planner,
    _normalize_item_type_str_for_import_helpers,
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

    assert _extract_planner_url_and_id_from_planner(planner_url) == (f"{PLANNER_API_BASE_URL}test-profile", 2, False)
    get.assert_called_once_with(url=f"{PLANNER_API_BASE_URL}test-profile")


def test_maxroll_planner_numeric_fragment_is_visible_position(mocker) -> None:
    planner_url = f"{PLANNER_BASE_URL}test-profile#3"

    assert _extract_planner_url_and_id_from_planner(planner_url) == (f"{PLANNER_API_BASE_URL}test-profile", 2, True)
