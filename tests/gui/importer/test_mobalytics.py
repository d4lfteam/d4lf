import json
import os
import typing
from types import SimpleNamespace

import pytest

from src.dataloader import Dataloader
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.mobalytics import _extract_mobalytics_season_number, import_mobalytics

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
    full_script_data_json = {
        "Diablo4Query:{}": {"documents": {"data": {"__ref": "Document:1"}}},
        "Document:1": {
            "tags": {"data": [{"groupSlug": "class", "name": "Sorcerer"}, {"groupSlug": "season", "name": "Season 12"}]}
        },
    }

    assert _extract_mobalytics_season_number(full_script_data_json, "Document:1") == "12"


def test_extract_mobalytics_season_number_returns_empty_without_tag_metadata() -> None:
    assert not _extract_mobalytics_season_number({}, "Document:1")


def test_import_mobalytics_uses_season_parameter_for_default_file_name(mocker: MockerFixture) -> None:
    full_script_data_json = {
        "Diablo4Query:{}": {"documents": {"data": {"__ref": "Document:1"}}},
        "Document:1": {
            "data": {
                "name": "Whirlwind Leveling Barb",
                "buildVariants": {
                    "values": [{"id": "variant-1", "genericBuilder": {"slots": [{"gameEntity": {"type": "ignored"}}]}}]
                },
            },
            "tags": {
                "data": [{"groupSlug": "class", "name": "Barbarian"}, {"groupSlug": "season", "name": "Season 12"}]
            },
        },
        "NgfDocumentCmWidgetContentVariantsV1DataChildVariant:variant-1": {"title": "Starter"},
    }
    html = f"<html><body><script>window.__PRELOADED_STATE__={json.dumps(full_script_data_json)};</script></body></html>"
    mocker.patch("src.gui.importer.mobalytics.get_with_retry", return_value=SimpleNamespace(text=html))
    save_as_profile = mocker.patch("src.gui.importer.mobalytics.save_as_profile", return_value="saved_profile")

    config = ImportConfig(
        url="https://mobalytics.gg/diablo-4/builds/example",
        import_uniques=False,
        import_aspect_upgrades=False,
        add_to_profiles=False,
        import_greater_affixes=False,
        require_greater_affixes=False,
        custom_file_name=None,
    )

    import_mobalytics(config=config)

    save_as_profile.assert_called_once()
    assert save_as_profile.call_args.kwargs["file_name"] == "mobalytics_barbarian_s12_whirlwind_leveling_barb_starter"


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
