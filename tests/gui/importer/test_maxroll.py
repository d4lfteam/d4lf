import os
import typing
from types import SimpleNamespace

import pytest

from src.dataloader import Dataloader
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.maxroll import (
    PLANNER_API_BASE_URL,
    _apply_guide_season_override,
    _extract_planner_url_and_id_from_guide,
    import_maxroll,
)

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


def test_apply_guide_season_override_replaces_stale_short_marker() -> None:
    assert _apply_guide_season_override("S11 Crackling Energy Sorc", "12") == "S12 Crackling Energy Sorc"
