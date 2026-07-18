import typing
from typing import override

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from src.importing.d4builds import constants as d4builds_constants
from src.importing.d4builds import extraction as _d4builds_helpers
from src.item import ItemType

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from selenium.webdriver.support.relative_locator import RelativeBy

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

    seal_filter = _d4builds_helpers._create_seal_filter_from_tooltip_html(tooltip_html=tooltip_html, require_gas=False)
    if seal_filter is None:
        pytest.fail("Expected seal tooltip to produce a filter")

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

    charm_filter, set_name = _d4builds_helpers._create_charm_filter_from_tooltip_html(
        tooltip_html=tooltip_html, require_gas=False
    )
    if charm_filter is None:
        pytest.fail("Expected charm tooltip to produce a filter")

    assert set_name == "berserkers_crucible"
    assert charm_filter.set == ["berserkers_crucible"]
    assert [affix.name for affix in charm_filter.affix_pool[0].count] == ["maximum_resource"]


def test_create_charm_filter_from_tooltip_html_does_not_guess_set_from_title() -> None:
    tooltip_html = """
        <div class="charm__tooltip">
            <h2 class="charm__tooltip__name">Fer of Balazan's Bite</h2>
            <ul class="charm__tooltip__values">
                <li class="charm__tooltip__value">Maximum Resource</li>
            </ul>
        </div>
    """

    charm_filter, set_name = _d4builds_helpers._create_charm_filter_from_tooltip_html(
        tooltip_html=tooltip_html, require_gas=False
    )
    if charm_filter is None:
        pytest.fail("Expected charm tooltip to produce a filter")

    assert not set_name
    assert charm_filter.set == []
    assert [affix.name for affix in charm_filter.affix_pool[0].count] == ["maximum_resource"]


def test_create_charm_filter_from_tooltip_html_reads_unique_aspect() -> None:
    tooltip_html = """
        <div class="charm__tooltip">
            <h2 class="charm__tooltip__name charm__tooltip__name--unique">Fractured Winterglass</h2>
        </div>
    """

    charm_filter, set_name = _d4builds_helpers._create_charm_filter_from_tooltip_html(
        tooltip_html=tooltip_html, require_gas=False
    )
    if charm_filter is None:
        pytest.fail("Expected charm tooltip to produce a filter")

    assert not set_name
    assert charm_filter.affix_pool == []
    assert [unique_aspect.name for unique_aspect in charm_filter.unique_aspect] == ["fractured_winterglass"]


def test_weapon_type_from_unique_tooltip_html_reads_bow() -> None:
    tooltip_html = """
        <div class="unique__tooltip unique__tooltip--mythic">
            <h2 class="unique__tooltip__name">Eaglehorn</h2>
            <div class="unique__tooltip__slot unique__tooltip__slot--mythic">Mythic Unique Bow</div>
        </div>
    """

    assert _d4builds_helpers._weapon_type_from_unique_tooltip_html(tooltip_html) == ItemType.Bow


def test_weapon_type_from_unique_tooltip_html_reads_one_handed_dagger() -> None:
    tooltip_html = """
        <div class="unique__tooltip">
            <h2 class="unique__tooltip__name">Etna's Lost Dagger</h2>
            <div class="unique__tooltip__slot">Unique 1h Dagger</div>
        </div>
    """

    assert _d4builds_helpers._weapon_type_from_unique_tooltip_html(tooltip_html) == ItemType.Dagger


def test_weapon_type_from_unique_tooltip_html_returns_none_for_aspect_tooltip() -> None:
    """Generic legendary weapons (aspect only, no unique) show a codex tooltip with no type info."""
    tooltip_html = """
        <div class="codex__tooltip">
            <div class="codex__tooltip__header">
                <div class="codex__tooltip__name">Aspect of Imitated Imbuement</div>
            </div>
        </div>
    """

    assert _d4builds_helpers._weapon_type_from_unique_tooltip_html(tooltip_html) is None


def test_weapon_type_from_unique_tooltip_html_returns_none_for_empty_html() -> None:
    assert _d4builds_helpers._weapon_type_from_unique_tooltip_html("") is None


class _FakePaperdollItem(WebElement):
    def __init__(self, slot_text: str, icon: WebElement) -> None:
        self._slot_text = slot_text
        self._icon = icon

    @override
    def find_elements(self, by: str = By.ID, value: str | None = None) -> list[WebElement]:
        if value is None:
            value = str(by)
        if value == d4builds_constants.PAPERDOLL_ITEM_SLOT_CSS:
            return [_FakeTextElement(self._slot_text)]
        if value == d4builds_constants.PAPERDOLL_GEAR_ICON_CSS:
            return [self._icon]
        msg = f"unexpected selector: {value}"
        raise AssertionError(msg)


class _FakeIcon(WebElement):
    def __init__(self) -> None:
        pass


class _FakeTextElement(WebElement):
    def __init__(self, text: str) -> None:
        self._text = text

    @property
    @override
    def text(self) -> str:
        return self._text


def test_get_weapon_paperdoll_icons_maps_slot_to_icon_without_hovering(mocker: MockerFixture) -> None:
    bow_icon, dagger_icon = _FakeIcon(), _FakeIcon()
    items: list[WebElement] = [
        _FakePaperdollItem("Ranged Weapon", bow_icon),
        _FakePaperdollItem("Dual-Wield Weapon 1", dagger_icon),
    ]

    class _FakeDriver(WebDriver):
        def __init__(self) -> None:
            pass

        @override
        def find_elements(self, by: str | RelativeBy = By.ID, value: str | None = None) -> list[WebElement]:
            if value is None:
                value = str(by)
            assert value == d4builds_constants.PAPERDOLL_WEAPON_ITEM_CSS
            return list(items)

    hover_spy = mocker.patch.object(_d4builds_helpers, "hover_and_get_tooltip_html")

    result = _d4builds_helpers._get_weapon_paperdoll_icons(driver=_FakeDriver())

    assert result == {"Ranged Weapon": bow_icon, "Dual-Wield Weapon 1": dagger_icon}
    hover_spy.assert_not_called()


def test_get_weapon_paperdoll_icons_renames_2h_weapon_slot() -> None:
    staff_icon = _FakeIcon()

    class _FakeDriver(WebDriver):
        def __init__(self) -> None:
            pass

        @override
        def find_elements(self, by: str | RelativeBy = By.ID, value: str | None = None) -> list[WebElement]:
            if value is None:
                value = str(by)
                assert value == d4builds_constants.PAPERDOLL_WEAPON_ITEM_CSS
            return [_FakePaperdollItem("2H Weapon", staff_icon)]

    result = _d4builds_helpers._get_weapon_paperdoll_icons(driver=_FakeDriver())

    assert result == {"Weapon": staff_icon}


def test_get_weapon_type_from_paperdoll_tooltip_hovers_given_icon(mocker: MockerFixture) -> None:
    icon = _FakeIcon()
    mocker.patch.object(
        _d4builds_helpers,
        "hover_and_get_tooltip_html",
        return_value='<div class="unique__tooltip"><div class="unique__tooltip__slot">Mythic Unique Bow</div></div>',
    )

    result = _d4builds_helpers._get_weapon_type_from_paperdoll_tooltip(driver=mocker.Mock(), icon=icon)

    assert result == ItemType.Bow


def test_match_d4builds_tooltip_affix_uses_guessed_charm_set_for_seal_affixes() -> None:
    affix_name = _d4builds_helpers._match_d4builds_tooltip_affix(
        text="Maximum Resolve", item_type=ItemType.HoradricSeal, guessed_set_name="arms_of_arreat"
    )

    assert affix_name == "arms_of_arreat_maximum_resolve"


def test_match_d4builds_tooltip_affix_keeps_generic_seal_match_with_guessed_set() -> None:
    affix_name = _d4builds_helpers._match_d4builds_tooltip_affix(
        text="Cooldown Reduction", item_type=ItemType.HoradricSeal, guessed_set_name="arms_of_arreat"
    )

    assert affix_name == "cooldown_reduction"
