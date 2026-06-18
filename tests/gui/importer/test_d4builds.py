import os
import typing

import lxml.html
import pytest

from src.dataloader import Dataloader
from src.gui.importer import d4builds as d4builds_module
from src.gui.importer import paragon_export as paragon_export_module
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.paragon_export import build_paragon_profile_payload
from src.item.data.item_type import ItemType

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
            <div class="builder__header__title">
                <div class="builder__header__selection builder__header__selection--planner">
                    <h1 class="builder__header__name">
                        <span>Necromancer Build</span>
                        <form class="builder__header__form">
                            <input class="builder__header__input" value="Rob&#39;s Golem Minion Necro (S4) Pit 142+">
                        </form>
                    </h1>
                </div>
            </div>
            <div class="variant__navigation">
                <input class="builder__variant__input" value="Standard Build">
            </div>
        </div>
        <div class="builder__gear">
            <div class="builder__dropdown__wrapper">
                <div class="dropdown">
                    <div class="dropdown__button">Season 4</div>
                </div>
            </div>
        </div>
    """)

    assert d4builds_module._extract_build_metadata(data) == (
        "Necromancer",
        "Rob's Golem Minion Necro (S4) Pit 142+",
        "4",
        "Standard Build",
    )


def test_extract_build_metadata_prefers_description_for_guides() -> None:
    data = lxml.html.fromstring("""
        <div class="builder">
          <div class="builder__header">
            <h1 class="builder__header__name">Blessed Shield Paladin Build Guide - Diablo 4</h1>
            <h2 class="builder__header__description">Rob's Cpt. America (S12)</h2>
            <div class="variant__navigation">
                <input class="builder__variant__input" value="Pit Push (Glasscannon)">
            </div>
          </div>
          <div class="builder__gear">
            <div class="builder__dropdown__wrapper">
                <div class="dropdown">
                    <div class="dropdown__button">Season 12</div>
                </div>
            </div>
          </div>
        </div>
    """)

    assert d4builds_module._extract_build_metadata(data) == (
        "Paladin",
        "Rob's Cpt. America (S12)",
        "12",
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

    assert d4builds_module._extract_d4builds_season_number(data) == "12"


def test_create_seal_filter_from_tooltip_html_matches_tooltip_values() -> None:
    tooltip_html = """
        <div class="seal__tooltip">
            <h2 class="seal__tooltip__name">Seal</h2>
            <ul class="seal__tooltip__values">
                <li class="seal__tooltip__value seal__tooltip__value--base">
                    <span class="seal__tooltip__value__text">Critical Strike Damage</span>
                </li>
                <li class="seal__tooltip__value">
                    <span class="seal__tooltip__value__text">Attack Speed</span>
                </li>
                <li class="seal__tooltip__value">
                    <span class="seal__tooltip__value__text">+1 Unique Charm Slot</span>
                </li>
            </ul>
        </div>
    """

    seal_filter = d4builds_module._create_seal_filter_from_tooltip_html(tooltip_html=tooltip_html, require_gas=False)

    assert [affix.name for affix in seal_filter.affix_pool[0].count] == [
        "critical_strike_damage",
        "attack_speed",
        "charm_slot",
    ]


def test_create_charm_filter_from_tooltip_html_reads_set_name_and_affixes() -> None:
    tooltip_html = """
        <div class="charm__tooltip">
            <h2 class="charm__tooltip__name">Fer of the Crucible</h2>
            <ul class="charm__tooltip__values">
                <li class="charm__tooltip__value">Maximum Resource</li>
            </ul>
            <div class="charm__tooltip__set">
                <div class="charm__tooltip__set__name">Berserker's Crucible</div>
            </div>
        </div>
    """

    charm_filter, set_name = d4builds_module._create_charm_filter_from_tooltip_html(
        tooltip_html=tooltip_html, require_gas=False
    )

    assert set_name == "berserkers_crucible"
    assert charm_filter.set == ["berserkers_crucible"]
    assert [affix.name for affix in charm_filter.affix_pool[0].count] == ["maximum_resource"]


def test_match_d4builds_tooltip_affix_uses_guessed_charm_set_for_seal_affixes() -> None:
    affix_name = d4builds_module._match_d4builds_tooltip_affix(
        text="Maximum Resolve", item_type=ItemType.HoradricSeal, guessed_set_name="arms_of_arreat"
    )

    assert affix_name == "arms_of_arreat_maximum_resolve"


def test_match_d4builds_tooltip_affix_keeps_generic_seal_match_with_guessed_set() -> None:
    affix_name = d4builds_module._match_d4builds_tooltip_affix(
        text="Cooldown Reduction", item_type=ItemType.HoradricSeal, guessed_set_name="arms_of_arreat"
    )

    assert affix_name == "cooldown_reduction"


def test_parse_d4builds_paragon_boards_produces_valid_typed_payload_input() -> None:
    class _FakeTextNode:
        def __init__(self, text: str):
            self._text = text

        def get_attribute(self, name: str) -> str:
            return self._text if name == "innerText" else ""

    class _FakeTile:
        def __init__(self, class_name: str):
            self._class_name = class_name

        def get_attribute(self, name: str) -> str:
            return self._class_name if name == "class" else ""

    class _FakeBoardElement:
        def __init__(self):
            self._attrs = {"data-board-id": "Paragon_Barb_00"}

        def find_element(self, by, value):
            if value == "paragon__board__name":
                return _FakeTextNode("Starting Board")
            msg = f"unexpected selector: {value}"
            raise AssertionError(msg)

        def find_elements(self, by, value):
            if value == "paragon__board__name__glyph":
                return [_FakeTextNode("Glyph Name")]
            if value == "paragon__board__tile":
                return [_FakeTile("paragon__board__tile r2 c10 active enabled")]
            msg = f"unexpected selector: {value}"
            raise AssertionError(msg)

        def get_attribute(self, name: str) -> str:
            return "transform: rotate(90deg);" if name == "style" else ""

    class _FakeDriver:
        def execute_script(self, script, board_elem):
            return board_elem._attrs

        def find_elements(self, by, value):
            if value == "paragon__board":
                return [_FakeBoardElement()]
            msg = f"unexpected selector: {value}"
            raise AssertionError(msg)

    boards = paragon_export_module._parse_d4builds_paragon_boards(_FakeDriver(), class_slug="barbarian")
    payload = build_paragon_profile_payload("Build Name", "https://example.invalid", boards)

    board = payload.paragon_boards_list[0][0]
    assert board.name == "barbarian-paragon-barb-00"
    assert board.rotation == "90°"
    assert board.nodes.count(True) == 1


@pytest.mark.parametrize("url", URLS)
@pytest.mark.selenium
@pytest.mark.skipif(not IN_GITHUB_ACTIONS, reason="Importer tests are skipped if not run from Github Actions")
def test_import_d4builds(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
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
    d4builds_module.import_d4builds(config=config)
