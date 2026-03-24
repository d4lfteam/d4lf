import os
import typing

import lxml.html
import pytest

from src.dataloader import Dataloader
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.mobalytics import (
    _apply_mobalytics_season_to_build_header,
    _extract_mobalytics_season_number,
    import_mobalytics,
)

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture
IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

URLS = [
    # No frills and no uniques
    "https://mobalytics.gg/diablo-4/builds/barbarian-whirlwind-leveling-barb",
    # Is a variant of the one above
    "https://mobalytics.gg/diablo-4/builds/barbarian-whirlwind-leveling-barb?ws-ngf5-1=activeVariantId%2C7a9c6d51-18e9-4090-a804-7b73ff00879d",
    # A standard build with uniques
    "https://mobalytics.gg/diablo-4/builds/necromancer-skeletal-warrior-minions",
    # This one has no variants at all, just to make sure that works too
    "https://mobalytics.gg/diablo-4/profile/screamheart/builds/15x-thrash-out-of-date",
    # This one has an item type for the weapon
    "https://mobalytics.gg/diablo-4/builds/druid-zaior-pulverize-druid",
    # This has two rogue offhand weapons
    "https://mobalytics.gg/diablo-4/builds/rogue-efficientrogue-dance-of-knives?ws-ngf5-1=activeVariantId%2Ca2977139-f3e2-4b13-aa64-82ba69972528",
]


def test_extract_mobalytics_season_number_from_tag_metadata() -> None:
    data = lxml.html.fromstring("<html><body></body></html>")
    full_script_data_json = {
        "Diablo4Query:{}": {"documents": {"data": {"__ref": "Document:1"}}},
        "Document:1": {
            "tags": {"data": [{"groupSlug": "class", "name": "Sorcerer"}, {"groupSlug": "season", "name": "Season 12"}]}
        },
    }

    assert _extract_mobalytics_season_number(full_script_data_json, "Document:1", data) == "12"


def test_extract_mobalytics_season_number_from_top_level_page_text() -> None:
    data = lxml.html.fromstring("""
        <html>
          <body>
            <h1>MrRonit's Charge Auradin (1 Button Zoomer/AFK Build)</h1>
            <div>Paladin</div>
            <div>Season 12</div>
            <div>Updated on Mar 11, 2026</div>
            <h2>Build Overview</h2>
            <p>This section may mention older seasons later on.</p>
          </body>
        </html>
    """)

    assert _extract_mobalytics_season_number({}, "Document:1", data) == "12"


def test_apply_mobalytics_season_to_build_header_prefixes_when_missing() -> None:
    assert _apply_mobalytics_season_to_build_header("MrRonit's Charge Auradin", "12") == (
        "S12 MrRonit's Charge Auradin"
    )


@pytest.mark.parametrize("url", URLS)
@pytest.mark.requests
@pytest.mark.skipif(not IN_GITHUB_ACTIONS, reason="Importer tests are skipped if not run from Github Actions")
def test_import_mobalytics(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
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
    import_mobalytics(config=config)
