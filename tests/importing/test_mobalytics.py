import json
import logging
import os
import typing

import pytest
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webdriver import WebDriver

import src.importing.mobalytics._extraction as mobalytics_module
from src.importing import ImportOptions, ImportRequest
from src.importing.mobalytics._extraction import (
    _as_text,
    _convert_raw_to_affixes,
    _extract_mobalytics_charm_set_name,
    _first_jsonpath_result,
    _get_weapon_slot_trigger,
    _get_weapon_type_from_slot_tooltip,
    _log_mobalytics_page_diagnostics,
)
from src.importing.paragon_export import build_paragon_profile_payload, extract_mobalytics_paragon_steps
from src.item.data.item_type import ItemType
from src.profiles import ParagonPayloadModel

if typing.TYPE_CHECKING:
    from collections.abc import Mapping

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


def _request(
    *,
    url: str,
    import_aspect_upgrades: bool = True,
    add_to_profiles: bool = False,
    import_greater_affixes: bool = False,
    require_greater_affixes: bool = False,
    custom_file_name: str | None = None,
) -> ImportRequest:
    return ImportRequest(
        url=url,
        options=ImportOptions(
            import_aspect_upgrades=import_aspect_upgrades,
            add_to_profiles=add_to_profiles,
            import_greater_affixes=import_greater_affixes,
            require_greater_affixes=require_greater_affixes,
            custom_file_name=custom_file_name,
        ),
    )


class _MobalyticsDiagnosticsDriver(WebDriver):
    def __init__(self) -> None:
        pass

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


def _mobalytics_page_source(slots: list[Mapping[str, object]]) -> str:
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
    slot: str, entity_type: str, title: str, modifiers: Mapping[str, object] | None = None, icon_url: str = ""
) -> dict[str, object]:
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


@pytest.mark.parametrize("value", [None, 7, False])
def test_as_text_rejects_non_string_remote_values(value: object) -> None:
    assert not _as_text(value)


def test_first_jsonpath_result_returns_none_for_missing_data() -> None:
    assert _first_jsonpath_result("$.missing", {"present": True}) is None


@pytest.mark.parametrize(("rotation", "expected_index"), [(0, 283), (90, 217), (180, 157), (270, 223)])
def test_extract_mobalytics_paragon_steps_keeps_rotation_index_mapping(rotation: int, expected_index: int) -> None:
    steps = extract_mobalytics_paragon_steps({
        "boards": [{"board": {"slug": "barbarian-starting-board"}, "glyph": {"slug": ""}, "rotation": rotation}],
        "nodes": [{"slug": "barbarian-starting-board-x11-y14"}],
    })

    board = steps[0][0]
    assert board["Rotation"] == f"{rotation}°"
    assert board["Nodes"].count(True) == 1
    assert board["Nodes"][expected_index] is True


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
    caplog.set_level(logging.DEBUG, logger="src.importing.mobalytics")

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
    ("title", "icon_url", "expected_set_name"),
    [
        (
            "Fer of the Den Mother",
            "https://cdn.mobalytics.gg/assets/diablo-4/images/charms/might-of-the-den-mother.png",
            "might_of_the_den_mother",
        ),
        (
            "Fer of Bul-Kathos' Pride",
            "https://cdn.mobalytics.gg/assets/diablo-4/images/charms/bul-kathos-pride.png",
            "bul-kathos_pride",
        ),
        ("Arreat's Bearing", "https://cdn.mobalytics.gg/assets/diablo-4/images/charms/unique-charm.png", None),
    ],
)
def test_extract_mobalytics_charm_set_name_from_icon_url(
    title: str, icon_url: str, expected_set_name: str | None
) -> None:
    item = _mobalytics_slot(slot="season-12-charm-1", entity_type="charms", title=title, icon_url=icon_url)

    assert _extract_mobalytics_charm_set_name(item) == expected_set_name


def test_get_weapon_slot_trigger_looks_up_span_by_humanized_slot_title(mocker: MockerFixture) -> None:
    driver = mocker.Mock()

    _get_weapon_slot_trigger(driver=driver, slot_type="dual-wield-weapon-1")

    (by, xpath), _kwargs = driver.find_element.call_args
    assert "Dual wield weapon 1" in xpath


def test_get_weapon_slot_trigger_returns_none_when_not_found(mocker: MockerFixture) -> None:
    driver = mocker.Mock()
    driver.find_element.side_effect = NoSuchElementException

    assert _get_weapon_slot_trigger(driver=driver, slot_type="weapon") is None


def test_get_weapon_type_from_slot_tooltip_reads_mythic_unique_type(mocker: MockerFixture) -> None:
    mocker.patch.object(mobalytics_module, "_get_weapon_slot_trigger", return_value=object())
    mocker.patch.object(
        mobalytics_module,
        "hover_and_get_tooltip_html",
        return_value="<div><p>Sundered Night</p><p>Mythic Unique 2h Axe</p><p>description</p></div>",
    )

    assert _get_weapon_type_from_slot_tooltip(driver=mocker.Mock(), slot_type="weapon") == ItemType.Axe2H


def test_get_weapon_type_from_slot_tooltip_returns_none_for_legendary_aspect_tooltip(mocker: MockerFixture) -> None:
    """Generic legendary weapons (aspect only, no unique) show a tooltip with no type info."""
    mocker.patch.object(mobalytics_module, "_get_weapon_slot_trigger", return_value=object())
    mocker.patch.object(
        mobalytics_module,
        "hover_and_get_tooltip_html",
        return_value="<div><p>Aspect of Glynn's Anvil</p><p>Legendary Aspect</p><p>description</p></div>",
    )

    assert _get_weapon_type_from_slot_tooltip(driver=mocker.Mock(), slot_type="weapon") is None


def test_get_weapon_type_from_slot_tooltip_returns_none_when_trigger_missing(mocker: MockerFixture) -> None:
    mocker.patch.object(mobalytics_module, "_get_weapon_slot_trigger", return_value=None)
    hover_spy = mocker.patch.object(mobalytics_module, "hover_and_get_tooltip_html")

    assert _get_weapon_type_from_slot_tooltip(driver=mocker.Mock(), slot_type="weapon") is None
    hover_spy.assert_not_called()
