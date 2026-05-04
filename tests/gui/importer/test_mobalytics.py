import json
import os
import typing
from types import SimpleNamespace

import pytest

from src.dataloader import Dataloader
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.mobalytics import import_mobalytics

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


def test_import_mobalytics_skips_slots_without_importable_affixes(mocker: MockerFixture) -> None:
    build_data = {
        "name": "Profane Sentinel Warlock Endgame Build Guide",
        "buildVariants": {
            "values": [
                {
                    "id": "variant-1",
                    "genericBuilder": {
                        "slots": [
                            {
                                "gameEntity": {
                                    "type": "aspects",
                                    "entity": {"title": "Legendary Helm"},
                                    "modifiers": {"gearStats": [], "implicitStats": [{"id": "2h-sword"}]},
                                },
                                "gameSlotSlug": "weapon",
                            }
                        ]
                    },
                    "paragon": {},
                }
            ]
        },
    }
    preloaded_state = {
        "userGeneratedDocumentBySlug": {
            "data": {
                "data": build_data,
                "tags": {
                    "data": [{"groupSlug": "class", "name": "Warlock"}, {"groupSlug": "season", "name": "Season 13"}]
                },
            }
        },
        "childrenVariants": [],
    }
    html = f"<html><script>window.__PRELOADED_STATE__={json.dumps(preloaded_state)};</script></html>"
    mocker.patch("src.gui.importer.mobalytics.get_with_retry", return_value=SimpleNamespace(text=html))
    save_profile_mock = mocker.patch("src.gui.importer.mobalytics.save_as_profile", return_value="imported")

    config = ImportConfig(
        url="https://mobalytics.gg/diablo-4/builds/warlock-profane-sentinel-endgame",
        import_uniques=True,
        import_aspect_upgrades=True,
        add_to_profiles=False,
        import_greater_affixes=True,
        require_greater_affixes=True,
        custom_file_name=None,
    )

    import_mobalytics(config=config)

    save_profile_mock.assert_called_once()
    profile = save_profile_mock.call_args.kwargs["profile"]
    assert profile.Affixes == []


def test_import_mobalytics_loads_profile_build_by_id_when_preloaded_state_is_empty(mocker: MockerFixture) -> None:
    html = (
        "<html><script>window.__PRELOADED_STATE__="
        '{"diablo4State":{"apollo":{"graphqlV2":{"queries":[]}}}};'
        "</script></html>"
    )
    mobalytics_payload = {
        "data": {
            "game": {
                "documents": {
                    "userGeneratedDocumentById": {
                        "error": None,
                        "data": {
                            "id": "df95afa9-619e-4dc6-b5b6-0405830695be",
                            "slugifiedName": "ancient-leap",
                            "tags": {
                                "data": [
                                    {"groupSlug": "class", "slug": "barbarian", "name": "Barbarian"},
                                    {"groupSlug": "season", "slug": "season-13", "name": "Season 13"},
                                ]
                            },
                            "data": {
                                "name": "Ancient Leap",
                                "childrenIds": ["root"],
                                "buildVariants": {
                                    "values": [
                                        {
                                            "id": "2",
                                            "genericBuilder": {
                                                "slots": [
                                                    {
                                                        "gameSlotSlug": "chest-armor",
                                                        "gameEntity": {
                                                            "type": "aspects",
                                                            "entity": {"title": "Battle Fervor's Aspect"},
                                                            "modifiers": {
                                                                "gearStats": [
                                                                    {"id": "strength", "isGreater": False},
                                                                    {"id": "maximum-life", "isGreater": False},
                                                                    {"id": "fury-per-second", "isGreater": False},
                                                                    {"id": "ranks-to-rallying-cry", "isGreater": True},
                                                                ],
                                                                "implicitStats": [None],
                                                            },
                                                        },
                                                    }
                                                ]
                                            },
                                            "paragon": {
                                                "boards": [
                                                    {
                                                        "x": 0,
                                                        "y": 0,
                                                        "rotation": 0,
                                                        "board": {"slug": "barbarian-starter-board"},
                                                        "glyph": {"slug": "barbarian-marshal"},
                                                        "glyphLevel": 100,
                                                    }
                                                ],
                                                "nodes": [{"slug": "barbarian-starter-board-x1-y1"}],
                                                "priorityList": [],
                                            },
                                        }
                                    ]
                                },
                            },
                        },
                    }
                }
            }
        }
    }

    class MockResponse:
        def raise_for_status(self) -> None:
            return

        def json(self) -> dict:
            return mobalytics_payload

    mocker.patch("src.gui.importer.mobalytics.get_with_retry", return_value=SimpleNamespace(text=html))
    post_mock = mocker.patch("src.gui.importer.mobalytics.httpx.post", return_value=MockResponse())
    save_profile_mock = mocker.patch("src.gui.importer.mobalytics.save_as_profile", return_value="imported")

    config = ImportConfig(
        url="https://mobalytics.gg/diablo-4/profile/cliptis/builds/df95afa9-619e-4dc6-b5b6-0405830695be",
        import_uniques=True,
        import_aspect_upgrades=True,
        add_to_profiles=False,
        import_greater_affixes=True,
        require_greater_affixes=True,
        export_paragon=True,
        custom_file_name=None,
    )

    import_mobalytics(config=config)

    post_mock.assert_called_once()
    query = post_mock.call_args.kwargs["json"]["query"]
    assert "paragon" in query
    profile = save_profile_mock.call_args.kwargs["profile"]
    assert len(profile.Affixes) == 1
    item_filter = next(iter(profile.Affixes[0].root.values()))
    assert item_filter.minGreaterAffixCount == 1
    assert profile.Paragon is not None
    assert profile.Paragon["ParagonBoardsList"][0][0]["Name"] == "barbarian-starting-board"
    assert profile.Paragon["ParagonBoardsList"][0][0]["Glyph"] == "barbarian-marshal"
