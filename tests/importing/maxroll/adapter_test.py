import json
import logging
import os
import typing
from types import SimpleNamespace

import pytest

from src.importing import ImportOptions, ImportRequest
from src.importing.maxroll import extract_maxroll_paragon_steps
from src.importing.maxroll.adapter import (
    _find_item_affixes,
    _find_item_type,
    _resolve_visible_profile_index,
    import_maxroll,
)
from src.item import Dataloader, ItemType

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
    "https://maxroll.gg/d4/planner/ce9zox0y#3",
]


@pytest.mark.parametrize("url", URLS)
@pytest.mark.requests
@pytest.mark.skipif(not IN_GITHUB_ACTIONS, reason="Importer tests are skipped if not run from Github Actions")
def test_import_maxroll(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
    Dataloader()  # need to load data first or the mock will make it impossible
    mocker.patch("builtins.open", new=mocker.mock_open())
    request = ImportRequest(
        url=url,
        options=ImportOptions(
            import_aspect_upgrades=True,
            add_to_profiles=False,
            import_greater_affixes=True,
            require_greater_affixes=True,
        ),
    )
    import_maxroll(request=request)


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


def test_import_maxroll_keeps_mythic_item_without_affixes(mock_ini_loader, mocker: MockerFixture) -> None:
    Dataloader()
    planner_response = mocker.Mock()
    planner_response.json.return_value = {
        "season": "14",
        "name": "Test Build",
        "class": "Barbarian",
        "data": json.dumps({
            "profiles": [{"name": "Default", "items": {"helm": 1}}],
            "items": {"1": {"id": "item-mythic-helm", "explicits": []}},
        }),
    }
    mapping_response = mocker.Mock()
    mapping_response.json.return_value = {
        "items": {"item-mythic-helm": {"magicType": 4, "name": "Harlequin Crest", "type": "Helm"}},
        "attributeDescriptions": {},
        "affixes": {},
        "skills": {},
    }
    mocker.patch("src.importing.maxroll.adapter.get_with_retry", side_effect=[planner_response, mapping_response])

    captured_profile = {}

    def fake_save_new(*, file_name, profile, source):
        captured_profile["profile"] = profile
        return SimpleNamespace(file_name=file_name)

    profile_store = mocker.Mock()
    profile_store.save_new.side_effect = fake_save_new
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=profile_store)

    result = import_maxroll(
        request=ImportRequest(
            url="https://maxroll.gg/d4/planner/test-profile#1",
            options=ImportOptions(
                import_aspect_upgrades=False,
                add_to_profiles=False,
                import_greater_affixes=True,
                require_greater_affixes=False,
                custom_file_name="test",
            ),
        )
    )

    assert result is not None
    assert result.source_name == "maxroll"
    assert result.selected_variant == "Default"
    assert result.saved_file_name == "test"
    assert result.paragon is None
    profile = captured_profile["profile"]
    assert {next(iter(entry.root)) for entry in profile.affixes} == {"Helm"}
    helm_filter = next(entry.root["Helm"] for entry in profile.affixes if "Helm" in entry.root)
    assert helm_filter.unique_aspect[0].name == "harlequin_crest"
    assert helm_filter.affix_pool == []


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


@pytest.mark.parametrize(
    ("affix_key", "attribute"),
    [
        ("X2_Transfiguration_DamageTypePercent_Fire", {"id": 255, "param": 1, "formula": "SancAffix_10%"}),
        ("X2_Transfiguration_AttackSpeed", {"id": 221, "formula": "SancAffix_10%"}),
    ],
)
def test_find_item_affixes_skips_transfiguration_affixes(affix_key, attribute, caplog) -> None:
    Dataloader()
    mapping_data = {"affixes": {affix_key: {"id": 1, "magicType": 0, "attributes": [attribute]}}, "skills": {}}

    with caplog.at_level(logging.INFO):
        affixes = _find_item_affixes(mapping_data=mapping_data, item_affixes=[{"nid": 1}], item_type=ItemType.Helm)

    assert affixes == []
    assert "Skipping Transfiguration affix" in caplog.messages[0]


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
