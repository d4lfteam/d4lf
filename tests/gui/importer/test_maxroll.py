import os
import typing

import pytest

from src.dataloader import Dataloader
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.maxroll import _find_item_affixes, _find_item_type, _resolve_visible_profile_index, import_maxroll
from src.gui.importer.paragon_export import extract_maxroll_paragon_steps
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


def test_resolve_visible_profile_index_skips_hidden_profiles() -> None:
    profiles = [
        {"name": "Any hidden variant name", "hidden": True},
        {"name": "Visible variant A"},
        {"name": "Visible variant B"},
        {"name": "Visible variant C"},
    ]

    assert _resolve_visible_profile_index(profiles=profiles, visible_profile_index=2) == 3


def test_find_item_affixes_resolves_skill_rank_category_from_affix_key() -> None:
    mapping_data = {
        "affixes": {
            "X2_SkillRankBonus_Sorc_Category_Shock": {
                "id": 1,
                "magicType": 0,
                "attributes": [{"id": 1155, "param": 332737186, "formula": "GearAffix_SkillRankBonus_1to2"}],
            }
        },
        "skills": {},
    }

    affixes = _find_item_affixes(mapping_data=mapping_data, item_affixes=[{"nid": 1}], item_type=ItemType.Amulet)

    assert [affix.name for affix in affixes] == ["to_shock_skills"]


def test_find_item_affixes_resolves_skill_rank_category_from_related_description() -> None:
    mapping_data = {
        "affixes": {
            "Unknown_SkillRankBonus": {
                "id": 1,
                "magicType": 0,
                "attributes": [{"id": 1155, "param": 1856650534, "formula": "GearAffix_SkillRankBonus"}],
            },
            "Talisman_SealAffix_Set_Rogue_05_UltimateSkillRanks": {
                "id": 2,
                "magicType": 1,
                "attributes": [{"id": 1155, "param": 1856650534, "formula": "GearAffix_SkillRankBonus"}],
                "desc": "+{c_number}[Skill_Rank_Skill_Tag_Bonus(1856650534)||]{/c} {c_important}Ultimate{/c} Skills",
            },
        },
        "skills": {},
    }

    affixes = _find_item_affixes(mapping_data=mapping_data, item_affixes=[{"nid": 1}], item_type=ItemType.Amulet)

    assert [affix.name for affix in affixes] == ["to_ultimate_skills"]


@pytest.mark.parametrize(("rotation", "expected_index"), [(0, 5), (1, 125), (2, 435), (3, 315)])
def test_extract_maxroll_paragon_steps_keeps_rotation_index_mapping(rotation: int, expected_index: int) -> None:
    steps = extract_maxroll_paragon_steps(
        active_profile={
            "paragon": {
                "steps": [{"data": [{"id": "Paragon_Barb_00", "glyph": "", "rotation": rotation, "nodes": {"5": 1}}]}]
            }
        },
        mapping_data={"paragonBoards": {"Paragon_Barb_00": {"name": "Starting Board"}}, "paragonGlyphs": {}},
    )

    board = steps[0][0]
    assert board["Rotation"] in {"0°", "90°", "180°", "270°"}
    assert board["Nodes"].count(True) == 1
    assert board["Nodes"][expected_index] is True
