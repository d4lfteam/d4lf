import json
import logging
import os
import typing

import pytest

from src.config.profile_models import ParagonPayloadModel
from src.dataloader import Dataloader
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.mobalytics import (
    _convert_raw_to_affixes,
    _extract_mobalytics_charm_set_name,
    _log_mobalytics_page_diagnostics,
    import_mobalytics,
)
from src.gui.importer.paragon_export import build_paragon_profile_payload, extract_mobalytics_paragon_steps
from src.item.data.item_type import ItemType

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


class _MobalyticsImportDriver:
    current_url = ""
    title = "Mobalytics"

    def __init__(self, page_source: str) -> None:
        self.page_source = page_source

    def get(self, url: str) -> None:
        self.current_url = url

    def find_element(self, *_args, **_kwargs) -> object:
        return object()

    def quit(self) -> None:
        return None


def _mobalytics_page_source(slots: list[dict]) -> str:
    build_data = {
        "name": "Pulverize Druid",
        "buildVariants": {"values": [{"id": "variant-1", "genericBuilder": {"slots": slots}, "paragon": {}}]},
    }
    state = {
        "userGeneratedDocumentBySlug": {
            "data": {
                "data": build_data,
                "tags": {
                    "data": [{"groupSlug": "class", "name": "Druid"}, {"groupSlug": "season", "name": "Season 14"}]
                },
            }
        }
    }
    return f"<html><script>window.__PRELOADED_STATE__={json.dumps(state)};</script></html>"


def _mobalytics_slot(
    slot: str, entity_type: str, title: str, modifiers: dict | None = None, icon_url: str = ""
) -> dict:
    return {
        "gameSlotSlug": slot,
        "gameEntity": {
            "slug": title.lower().replace(" ", "-"),
            "title": title,
            "type": entity_type,
            "iconUrl": icon_url,
            "modifiers": modifiers,
            "entity": {},
        },
    }


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


def test_convert_raw_to_affixes_uses_guessed_charm_set_for_seal_affixes() -> None:
    affixes = _convert_raw_to_affixes(
        raw_stats=[{"id": "maximum-resolve"}], item_type=ItemType.HoradricSeal, guessed_set_name="arms_of_arreat"
    )

    assert [affix.name for affix in affixes] == ["arms_of_arreat_maximum_resolve"]


def test_convert_raw_to_affixes_keeps_generic_seal_match_with_guessed_set() -> None:
    affixes = _convert_raw_to_affixes(
        raw_stats=[{"id": "cooldown-reduction"}], item_type=ItemType.HoradricSeal, guessed_set_name="arms_of_arreat"
    )

    assert [affix.name for affix in affixes] == ["cooldown_reduction"]


@pytest.mark.parametrize(
    ("icon_url", "expected_set_name"),
    [
        (
            "https://cdn.mobalytics.gg/assets/diablo-4/images/charms/might-of-the-den-mother.png",
            "might_of_the_den_mother",
        ),
        ("https://cdn.mobalytics.gg/assets/diablo-4/images/charms/bul-kathos-pride.png", "bul-kathos_pride"),
        ("https://cdn.mobalytics.gg/assets/diablo-4/images/charms/unique-charm.png", None),
    ],
)
def test_extract_mobalytics_charm_set_name_from_icon_url(icon_url: str, expected_set_name: str | None) -> None:
    item = _mobalytics_slot(slot="season-12-charm-1", entity_type="charms", title="Charm", icon_url=icon_url)

    assert _extract_mobalytics_charm_set_name(item) == expected_set_name


def test_import_mobalytics_imports_set_charm_and_deduplicates_identical_rings(
    mock_ini_loader, mocker: MockerFixture
) -> None:
    captured_profile = {}
    ring_1_modifiers = {
        "gearStats": [
            {"id": "willpower"},
            {"id": "critical-strike-chance"},
            {"id": "vulnerable-damage-multiplier"},
            {"id": "critical-strike-damage-multiplier"},
        ],
        "implicitStats": [],
    }
    ring_2_modifiers = {
        "gearStats": [
            {"id": "willpower"},
            {"id": "critical-strike-chance"},
            {"id": "critical-strike-damage-multiplier"},
            {"id": "vulnerable-damage-multiplier"},
        ],
        "implicitStats": [],
    }
    charm_icon_url = "https://cdn.mobalytics.gg/assets/diablo-4/images/charms/might-of-the-den-mother.png"
    driver = _MobalyticsImportDriver(
        page_source=_mobalytics_page_source([
            _mobalytics_slot(slot="ring-1", entity_type="items", title="Ring", modifiers=ring_1_modifiers),
            _mobalytics_slot(slot="ring-2", entity_type="items", title="Ring", modifiers=ring_2_modifiers),
            _mobalytics_slot(
                slot="season-12-charm-1", entity_type="charms", title="Fer of the Den Mother", icon_url=charm_icon_url
            ),
        ])
    )

    def fake_save_as_profile(file_name, profile, url):
        captured_profile["profile"] = profile
        return file_name

    mocker.patch("src.gui.importer.mobalytics.save_as_profile", side_effect=fake_save_as_profile)

    import_mobalytics(
        config=ImportConfig(
            url="https://mobalytics.gg/diablo-4/builds/druid-zaior-pulverize-druid",
            import_aspect_upgrades=False,
            import_greater_affixes=False,
            require_greater_affixes=False,
            add_to_profiles=False,
            custom_file_name="test",
        ),
        driver=driver,
    )

    profile = captured_profile["profile"]
    assert len(profile.affixes) == 1
    assert next(iter(profile.affixes[0].root)) == "Ring(x2)"
    assert len(profile.charms) == 1
    charm_filter = next(iter(profile.charms[0].root.values()))
    assert charm_filter.set == ["might_of_the_den_mother"]


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
