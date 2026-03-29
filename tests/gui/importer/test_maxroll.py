import json
import os
import typing
from types import SimpleNamespace

import pytest

from src.dataloader import Dataloader
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.maxroll import (
    PLANNER_API_BASE_URL,
    MaxrollException,
    _extract_planner_url_and_id_from_guide,
    _find_item_type,
    import_maxroll,
)
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
        import_uniques=True,
        import_aspect_upgrades=True,
        add_to_profiles=False,
        import_greater_affixes=True,
        require_greater_affixes=True,
        custom_file_name=None,
    )
    import_maxroll(config=config)


def test_extract_planner_url_and_id_from_guide_uses_active_embed_tab(mocker: MockerFixture) -> None:
    html = """
    <html>
      <body>
        <h1>Example Build Guide - Season 12 - Slaughter</h1>
        <div class="d4-embed" data-d4-profile="411y2000" data-d4-type="paperdoll" data-d4-data="3,1,2,4">
          <div class="d4tools-wrapper">
            <div class="d4t-CompositePaperdoll">
              <ul class="d4t-tabs">
                <li class="">Starter</li>
                <li class="d4t-active">Ancestral</li>
                <li class="">Mythic</li>
                <li class="">Push</li>
              </ul>
            </div>
          </div>
        </div>
      </body>
    </html>
    """
    mocker.patch("src.gui.importer.maxroll.get_with_retry", return_value=SimpleNamespace(text=html))

    planner_url, build_id, guide_season = _extract_planner_url_and_id_from_guide(
        "https://maxroll.gg/d4/build-guides/example"
    )

    assert planner_url == f"{PLANNER_API_BASE_URL}411y2000"
    assert build_id == 0
    assert guide_season == "12"


def test_extract_planner_url_and_id_from_guide_prefers_open_in_planner_link(mocker: MockerFixture) -> None:
    html = """
    <html>
      <body>
        <h1>Example Build Guide - Season 12 - Slaughter</h1>
        <a href="https://maxroll.gg/d4/planner/builds">Planner Index</a>
        <figure class="embed relative mx-auto table mx-auto text-center">
          <div class="d4-embed" data-d4-profile="411y2000" data-d4-type="paperdoll" data-d4-data="3,1,2,4">
            <div class="d4tools-wrapper">
              <div class="d4t-CompositePaperdoll">
                <ul class="d4t-tabs">
                  <li class="">Starter</li>
                  <li class="d4t-active">Ancestral</li>
                  <li class="">Mythic</li>
                  <li class="">Push</li>
                </ul>
                <div class="d4t-PlannerLink d4t-Paperdoll">
                  <a href="https://maxroll.gg/d4/planner/411y2000#2" class="d4t-planner-link">Open in Planner</a>
                </div>
              </div>
            </div>
          </div>
        </figure>
      </body>
    </html>
    """
    mocker.patch("src.gui.importer.maxroll.get_with_retry", return_value=SimpleNamespace(text=html))

    planner_url, build_id, guide_season = _extract_planner_url_and_id_from_guide(
        "https://maxroll.gg/d4/build-guides/example"
    )

    assert planner_url == f"{PLANNER_API_BASE_URL}411y2000"
    assert build_id == 1
    assert guide_season == "12"


def test_extract_planner_url_and_id_from_guide_keeps_direct_embed_id(mocker: MockerFixture) -> None:
    html = """
    <html>
      <body>
        <h1>Example Build Guide - Season 12 - Slaughter</h1>
        <div class="d4-embed" data-d4-profile="411y2000" data-d4-type="paperdoll" data-d4-id="5"></div>
      </body>
    </html>
    """
    mocker.patch("src.gui.importer.maxroll.get_with_retry", return_value=SimpleNamespace(text=html))

    planner_url, build_id, guide_season = _extract_planner_url_and_id_from_guide(
        "https://maxroll.gg/d4/build-guides/example"
    )

    assert planner_url == f"{PLANNER_API_BASE_URL}411y2000"
    assert build_id == 4
    assert guide_season == "12"


def test_extract_planner_url_and_id_from_guide_reports_bug_for_missing_embed_profile_id(mocker: MockerFixture) -> None:
    html = """
    <html>
      <body>
        <h1>Example Build Guide - Season 12 - Slaughter</h1>
        <div class="d4-embed" data-d4-profile="411y2000" data-d4-type="paperdoll"></div>
      </body>
    </html>
    """
    mocker.patch("src.gui.importer.maxroll.get_with_retry", return_value=SimpleNamespace(text=html))

    with pytest.raises(MaxrollException) as exc_info:
        _extract_planner_url_and_id_from_guide("https://maxroll.gg/d4/build-guides/example")

    assert str(exc_info.value) == (
        "Couldn't resolve a planner profile from this Maxroll build guide. Use the planner link directly and "
        "please report a bug."
    )


def test_import_maxroll_keeps_guide_season_in_paragon_name(mocker: MockerFixture) -> None:
    build_data = {"items": {}, "profiles": [{"name": "Pit Push", "items": {}}]}

    mocker.patch(
        "src.gui.importer.maxroll._extract_planner_url_and_id_from_guide",
        return_value=("https://planners.maxroll.gg/profiles/d4/example", 0, "12"),
    )
    mocker.patch(
        "src.gui.importer.maxroll.get_with_retry",
        side_effect=[
            SimpleNamespace(
                json=lambda: {"data": json.dumps(build_data), "name": "S11 Crackling Energy Sorc", "class": "Sorcerer"}
            ),
            SimpleNamespace(json=lambda: {"items": {}}),
        ],
    )
    mocker.patch("src.gui.importer.maxroll.extract_maxroll_paragon_steps", return_value=[[{"Name": "Start"}]])
    save_as_profile = mocker.patch("src.gui.importer.maxroll.save_as_profile", return_value="saved_profile")

    config = ImportConfig(
        url="https://maxroll.gg/d4/build-guides/example",
        import_uniques=False,
        import_aspect_upgrades=False,
        add_to_profiles=False,
        import_greater_affixes=False,
        require_greater_affixes=False,
        export_paragon=True,
        custom_file_name=None,
    )

    import_maxroll(config=config)

    save_as_profile.assert_called_once()
    assert save_as_profile.call_args.kwargs["profile"].Paragon["Name"] == "S12 Crackling Energy Sorc_Pit Push"


def test_find_item_type_uses_fix_weapon_type_with_slot_context() -> None:
    assert (
        _find_item_type(
            mapping_data={"item-1": {"type": "2H Sword"}},
            value="item-1",
            slot_name="mainWeapon",
            class_name="Barbarian",
        )
        == ItemType.Sword2H
    )


def test_find_item_type_uses_fix_offhand_type_with_slot_and_class_context() -> None:
    assert (
        _find_item_type(
            mapping_data={"item-1": {"type": "FocusBookOffHand"}},
            value="item-1",
            slot_name="offHand",
            class_name="Sorcerer",
        )
        == ItemType.Focus
    )


def test_find_item_type_uses_fix_offhand_type_when_item_type_implies_offhand() -> None:
    assert (
        _find_item_type(
            mapping_data={"item-1": {"type": "1HFocus"}}, value="item-1", slot_name="weapon2", class_name="Sorcerer"
        )
        == ItemType.Focus
    )


def test_import_maxroll_keeps_custom_file_name_unchanged(mocker: MockerFixture) -> None:
    build_data = {"items": {}, "profiles": [{"name": "Pit Push", "items": {}}]}

    mocker.patch(
        "src.gui.importer.maxroll.get_with_retry",
        side_effect=[
            SimpleNamespace(
                json=lambda: {"data": json.dumps(build_data), "name": "Chain Lightning Sorcerer", "class": "Sorcerer"}
            ),
            SimpleNamespace(json=lambda: {"items": {}}),
        ],
    )
    save_as_profile = mocker.patch("src.gui.importer.maxroll.save_as_profile", return_value="custom_name")
    build_default_profile_file_name = mocker.patch("src.gui.importer.maxroll.build_default_profile_file_name")

    config = ImportConfig(
        url="https://maxroll.gg/d4/planner/example#1",
        import_uniques=False,
        import_aspect_upgrades=False,
        add_to_profiles=False,
        import_greater_affixes=False,
        require_greater_affixes=False,
        custom_file_name="my_custom_name",
    )

    import_maxroll(config=config)

    save_as_profile.assert_called_once()
    assert save_as_profile.call_args.kwargs["file_name"] == "my_custom_name"
    build_default_profile_file_name.assert_not_called()
