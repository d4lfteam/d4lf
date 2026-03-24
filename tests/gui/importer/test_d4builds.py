import os
import typing

import lxml.html
import pytest

from src.dataloader import Dataloader
from src.gui.importer.d4builds import (
    _apply_d4builds_season_to_build_header,
    _extract_build_metadata,
    _extract_d4builds_season_number,
    import_d4builds,
)
from src.gui.importer.importer_config import ImportConfig

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture
IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

URLS = [
    "https://d4builds.gg/builds/01953e1c-6ba5-4f3a-8ebe-73273beda61b",
    "https://d4builds.gg/builds/0704c20f-68a7-49ed-97da-fc51454a9906",
    "https://d4builds.gg/builds/23ae9cbb-933e-4a88-999c-2241654cc8e2",
    "https://d4builds.gg/builds/a3e80fe0-11a8-48b8-8255-f6540ebc1c1d",
    "https://d4builds.gg/builds/b0330cfb-0f79-4d6d-a362-129492fad6a9",
    "https://d4builds.gg/builds/ba06ccf8-4182-449a-bfb4-102f96b1041e",
    "https://d4builds.gg/builds/dbad6569-2e78-4c43-a831-c563d0a1e1ad",
    "https://d4builds.gg/builds/ef414fbd-81cd-49d1-9c8d-4938b278e2ee",
    "https://d4builds.gg/builds/f8298a54-dc67-41ab-8232-ddfd32bd80fa",
]


def test_extract_build_metadata_from_planner_header() -> None:
    data = lxml.html.fromstring("""
        <div class="builder__header">
            <div class="builder__header__class">
                <img class="builder__header__icon Necromancer" alt="Diablo 4 Necromancer">
            </div>
            <div class="builder__header__title">
                <div class="builder__header__selection builder__header__selection--planner">
                    <h1 class="builder__header__name">
                        <form class="builder__header__form">
                            <input class="builder__header__input" value="Rob&#39;s Golem Minion Necro (S4) Pit 142+">
                        </form>
                    </h1>
                </div>
                <h2 class="builder__header__description">Necromancer Build</h2>
            </div>
            <div class="variant__navigation">
                <input class="builder__variant__input" value="Standard Build">
            </div>
        </div>
    """)

    assert _extract_build_metadata(data, "Diablo 4 Necromancer Build · D4 Builds") == (
        "Necromancer",
        "S4 Rob's Golem Minion Necro Pit 142+",
        "Standard Build",
    )


def test_extract_build_metadata_prefers_description_for_guides() -> None:
    data = lxml.html.fromstring("""
        <div class="builder__header">
            <div class="builder__header__class">
                <img class="builder__header__icon Paladin" alt="Diablo 4 Paladin">
            </div>
            <h1 class="builder__header__name">Blessed Shield Paladin Build Guide - Diablo 4</h1>
            <h2 class="builder__header__description">Rob's Cpt. America (S12)</h2>
            <div class="variant__navigation">
                <input class="builder__variant__input" value="Pit Push (Glasscannon)">
            </div>
        </div>
    """)

    assert _extract_build_metadata(data, "Blessed Shield Paladin Build Guide - Diablo 4 · D4 Builds") == (
        "Paladin",
        "S12 Rob's Cpt. America",
        "Pit Push (Glasscannon)",
    )


def test_extract_d4builds_season_number_from_gear_dropdown() -> None:
    data = lxml.html.fromstring("""
        <div class="builder">
            <div class="builder__gear">
                <div class="builder__dropdown__wrapper">
                    <div class="dropdown">
                        <div class="dropdown__button">Season 12</div>
                    </div>
                </div>
                <div class="builder__gear__items season_12">
                    <div>Gear</div>
                </div>
            </div>
            <div>Active Runes</div>
            <div>Season 10 appears later in the page and should be ignored.</div>
        </div>
    """)

    assert _extract_d4builds_season_number(data) == "12"


def test_apply_d4builds_season_to_build_header_prefixes_when_missing() -> None:
    assert _apply_d4builds_season_to_build_header("Chain Lightning Sorcerer", "12") == "S12 Chain Lightning Sorcerer"


def test_apply_d4builds_season_to_build_header_moves_trailing_season_to_front() -> None:
    assert _apply_d4builds_season_to_build_header("Lunging Strike Barb S12", "12") == "S12 Lunging Strike Barb"


@pytest.mark.parametrize("url", URLS)
@pytest.mark.selenium
@pytest.mark.skipif(not IN_GITHUB_ACTIONS, reason="Importer tests are skipped if not run from Github Actions")
def test_import_d4builds(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
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
    import_d4builds(config=config)
