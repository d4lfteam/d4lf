import logging
import os
import typing

import pytest

from src.config.profile_models import ParagonPayloadModel
from src.dataloader import Dataloader
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.mobalytics import _log_mobalytics_page_diagnostics, import_mobalytics
from src.gui.importer.paragon_export import build_paragon_profile_payload, extract_mobalytics_paragon_steps

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


class _MobalyticsDiagnosticsDriver:
    current_url = "https://mobalytics.gg/blocked"
    title = "Access denied"


def test_extract_mobalytics_paragon_steps_normalizes_warlock_starting_board():
    steps = extract_mobalytics_paragon_steps({
        "boards": [{"board": {"slug": "warlock-starter-board"}, "glyph": {"slug": "warlock-hellforge"}, "rotation": 0}],
        "nodes": [{"slug": "warlock-starting-board-x11-y14"}],
    })

    board = steps[0][0]
    node_index = (14 - 1) * 21 + (11 - 1)

    assert board["Name"] == "warlock-starting-board"
    assert board["Nodes"].count(True) == 1
    assert board["Nodes"][node_index] is True


def test_build_paragon_profile_payload_returns_typed_model():
    payload = build_paragon_profile_payload(
        build_name="Build Name",
        source_url="https://example.invalid",
        paragon_boards_list=[
            [{"Name": "Starting Board", "Glyph": "glyph_name", "Rotation": 90, "Nodes": [False] * 441}]
        ],
    )

    assert isinstance(payload, ParagonPayloadModel)
    assert payload.name == "Build Name"
    assert payload.paragon_boards_list[0][0].rotation == "90°"


def test_log_mobalytics_page_diagnostics_reports_loaded_page_shape(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.DEBUG, logger="src.gui.importer.mobalytics")

    _log_mobalytics_page_diagnostics(
        driver=_MobalyticsDiagnosticsDriver(),
        page_source="<html><script>self.__next_f.push([])</script>captcha</html>",
        script_count=1,
    )

    assert "current_url='https://mobalytics.gg/blocked'" in caplog.text
    assert "title='Access denied'" in caplog.text
    assert "script_count=1" in caplog.text
    assert "self.__next_f, captcha" in caplog.text


@pytest.mark.parametrize("url", URLS)
@pytest.mark.requests
@pytest.mark.skipif(not IN_GITHUB_ACTIONS, reason="Importer tests are skipped if not run from Github Actions")
def test_import_mobalytics(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
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
    import_mobalytics(config=config)
