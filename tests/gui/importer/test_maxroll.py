import json
import os
import typing

import pytest

from src.dataloader import Dataloader
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.maxroll import (
    _extract_planner_url_and_id_from_planner,
    _find_item_affixes,
    _find_item_type,
    import_maxroll,
)
from src.item.data.affix import AffixType
from src.item.data.item_type import ItemType

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture
IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

URLS = [
    "https://maxroll.gg/d4/build-guides/auradin-guide",
    "https://maxroll.gg/d4/build-guides/blessed-hammer-paladin-guide",
    "https://maxroll.gg/d4/build-guides/double-swing-barbarian-guide",
    "https://maxroll.gg/d4/build-guides/evade-spiritborn-build-guide",
    "https://maxroll.gg/d4/build-guides/frozen-orb-sorcerer-guide",
    "https://maxroll.gg/d4/build-guides/minion-necromancer-guide",
    "https://maxroll.gg/d4/build-guides/quill-volley-spiritborn-guide",
    "https://maxroll.gg/d4/build-guides/shield-of-retribution-paladin-guide",
    "https://maxroll.gg/d4/build-guides/touch-of-death-spiritborn-guide",
]


@pytest.mark.parametrize("url", URLS)
@pytest.mark.requests
@pytest.mark.skipif(not IN_GITHUB_ACTIONS, reason="Importer tests are skipped if not run from Github Actions")
def test_import_maxroll(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
    Dataloader()  # need to load data first or the mock will make it impossible
    mocker.patch("builtins.open", new=mocker.mock_open())
    config = ImportConfig(
        url=url,
        import_aspect_upgrades=True,
        add_to_profiles=False,
        import_greater_affixes=True,
        require_greater_affixes=True,
        custom_file_name=None,
    )
    import_maxroll(config=config)


def test_find_item_type_uses_fix_weapon_type_with_slot_context() -> None:
    assert (
        _find_item_type(mapping_data={"item-1": {"type": "2H Sword"}}, value="item-1", class_name="Barbarian")
        == ItemType.Sword2H
    )


def test_find_item_type_uses_fix_offhand_type_with_slot_and_class_context() -> None:
    assert (
        _find_item_type(mapping_data={"item-1": {"type": "FocusBookOffHand"}}, value="item-1", class_name="Sorcerer")
        == ItemType.Focus
    )


def test_find_item_type_uses_fix_offhand_type_when_item_type_implies_offhand() -> None:
    assert (
        _find_item_type(mapping_data={"item-1": {"type": "1HFocus"}}, value="item-1", class_name="Sorcerer")
        == ItemType.Focus
    )


def test_extract_planner_url_uses_fragment_as_profile_id(mocker: MockerFixture) -> None:
    response = mocker.Mock()
    response.json.return_value = {"data": json.dumps({"activeProfile": 2})}
    get_with_retry = mocker.patch("src.gui.importer.maxroll.get_with_retry", return_value=response)

    api_url, profile_id = _extract_planner_url_and_id_from_planner("https://maxroll.gg/d4/planner/n51lwl0u#1")

    assert api_url == "https://planners.maxroll.gg/profiles/d4/n51lwl0u"
    assert profile_id == 0
    get_with_retry.assert_called_once_with(url=api_url)


def test_extract_planner_url_uses_active_profile_without_fragment(mocker: MockerFixture) -> None:
    response = mocker.Mock()
    response.json.return_value = {"data": json.dumps({"activeProfile": 2})}
    mocker.patch("src.gui.importer.maxroll.get_with_retry", return_value=response)

    api_url, profile_id = _extract_planner_url_and_id_from_planner("https://maxroll.gg/d4/planner/n51lwl0u")

    assert api_url == "https://planners.maxroll.gg/profiles/d4/n51lwl0u"
    assert profile_id == 2


def test_find_item_affixes_resolves_skill_group_from_mapping_entry() -> None:
    result = _find_item_affixes(
        mapping_data={
            "affixes": {"affix-1": {"id": "rank-core", "magicType": 0, "attributes": [{"id": 1033, "param": -123}]}},
            "skills": {},
            "skillTags": {"core": {"id": -123, "name": "Core"}},
        },
        item_affixes=[{"nid": "rank-core", "greater": True}],
        item_type=ItemType.ChestArmor,
        import_greater_affixes=True,
    )

    assert len(result) == 1
    assert result[0].name == "to_core_skills"
    assert result[0].type == AffixType.greater


def test_find_item_affixes_resolves_skill_group_from_string_map() -> None:
    result = _find_item_affixes(
        mapping_data={
            "affixes": {
                "affix-1": {"id": "rank-defensive", "magicType": 0, "attributes": [{"id": 1034, "param": -456}]}
            },
            "skills": {},
            "uiStrings": {"skillTag": {"-456": "Defensive Skills"}},
        },
        item_affixes=[{"nid": "rank-defensive"}],
        item_type=ItemType.ChestArmor,
    )

    assert len(result) == 1
    assert result[0].name == "to_defensive_skills"
