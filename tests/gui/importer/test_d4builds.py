import os
import typing

import lxml.html
import pytest

from src.dataloader import Dataloader
from src.gui.importer.d4builds import (
    PAPERDOLL_ITEM_NAME_XPATH,
    PAPERDOLL_ITEM_SLOT_XPATH,
    PAPERDOLL_ITEM_TOOLTIP_TARGET_XPATH,
    VISIBLE_TOOLTIP_TEXT_SCRIPT,
    _extract_build_metadata,
    _extract_d4builds_season_number,
    _get_item_slots,
    _get_item_types_from_paperdoll_tooltips,
    import_d4builds,
)
from src.gui.importer.importer_config import ImportConfig
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

    assert _extract_build_metadata(data) == (
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

    assert _extract_build_metadata(data) == ("Paladin", "Rob's Cpt. America (S12)", "12", "Pit Push (Glasscannon)")


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


def test_get_item_slots_extracts_unique_name_only() -> None:
    data = lxml.html.fromstring("""
        <div class="builder__gear__items">
            <div class="builder__gear__item">
                <div class="builder__gear__slot">Bludgeoning Weapon</div>
                <div class="builder__gear__name">Heavy Hitting Aspect</div>
            </div>
        </div>
    """)

    item_slots = _get_item_slots(data=data)

    assert not item_slots["Bludgeoning Weapon"]


def test_import_d4builds_reads_weapon_type_from_unfilled_stat(mocker: MockerFixture) -> None:
    Dataloader()
    html = """
        <div class="builder__header__name">Whirlwind Barbarian Endgame Build Guide - Diablo 4</div>
        <div class="builder__gear">
            <div class="builder__dropdown__wrapper">
                <div class="dropdown">
                    <div class="dropdown__button">Season 9</div>
                </div>
            </div>
            <div class="builder__gear__items">
                <div class="builder__gear__item">
                    <div class="builder__gear__slot">Bludgeoning Weapon</div>
                    <div class="builder__gear__name">Heavy Hitting Aspect</div>
                </div>
            </div>
        </div>
        <div class="builder__stats__list">
            <div class="builder__stats__group">
                <span class="builder__stats__slot"></span>
                <span class="builder__stats__slot"></span>Bludgeoning Weapon
                <div class="builder__stats__type">
                    <span>2h Mace: 392.7% Overpower Damage</span>
                </div>
                <div class="builder__stats__affix">
                    <div>
                        <div class="dropdown__button__wrapper">
                            <span></span>
                        </div>
                    </div>
                </div>
                <div class="builder__stats__affix filled">
                    <div>
                        <div class="dropdown__button__wrapper">
                            <span>Strength</span>
                        </div>
                    </div>
                </div>
                <div class="builder__stats__affix filled">
                    <div>
                        <div class="dropdown__button__wrapper">
                            <span>Critical Strike Chance</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    """
    driver = mocker.Mock(page_source=html)
    driver.find_elements.return_value = []
    wait = mocker.Mock()
    wait.until.return_value = True
    mocker.patch("src.gui.importer.d4builds.WebDriverWait", return_value=wait)
    save_as_profile_mock = mocker.patch("src.gui.importer.d4builds.save_as_profile", return_value="profile")
    config = ImportConfig(
        url="https://d4builds.gg/builds/whirlwind-barbarian-endgame/?var=4",
        import_uniques=True,
        import_aspect_upgrades=False,
        add_to_profiles=False,
        import_greater_affixes=False,
        require_greater_affixes=False,
        custom_file_name="test",
    )

    import_d4builds(config=config, driver=driver)

    profile = save_as_profile_mock.call_args.kwargs["profile"]
    assert next(iter(profile.Affixes[0].root)) == "BludgeoningWeapon"
    item_filter = next(iter(profile.Affixes[0].root.values()))
    assert item_filter.itemType == [ItemType.Mace2H]


def test_import_d4builds_preserves_weapon_type_from_tooltip_map(mocker: MockerFixture) -> None:
    Dataloader()
    html = """
        <div class="builder__header__name">Whirlwind Barbarian Endgame Build Guide - Diablo 4</div>
        <div class="builder__gear">
            <div class="builder__dropdown__wrapper">
                <div class="dropdown">
                    <div class="dropdown__button">Season 9</div>
                </div>
            </div>
            <div class="builder__gear__items">
                <div class="builder__gear__item">
                    <div class="builder__gear__slot">Boots</div>
                    <div class="builder__gear__name">Aspect of Anger Management</div>
                </div>
                <div class="builder__gear__item">
                    <div class="builder__gear__slot">Bludgeoning Weapon</div>
                    <div class="builder__gear__name">Heavy Hitting Aspect</div>
                </div>
            </div>
        </div>
        <div class="builder__stats__list">
            <div class="builder__stats__group">
                <span class="builder__stats__slot"></span>
                <span class="builder__stats__slot"></span>Boots
                <div class="builder__stats__affix filled">
                    <div>
                        <div class="dropdown__button__wrapper">
                            <span>Strength</span>
                        </div>
                    </div>
                </div>
                <div class="builder__stats__affix filled">
                    <div>
                        <div class="dropdown__button__wrapper">
                            <span>Movement Speed</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="builder__stats__group">
                <span class="builder__stats__slot"></span>
                <span class="builder__stats__slot"></span>Bludgeoning Weapon
                <div class="builder__stats__affix filled">
                    <div>
                        <div class="dropdown__button__wrapper">
                            <span>Strength</span>
                        </div>
                    </div>
                </div>
                <div class="builder__stats__affix filled">
                    <div>
                        <div class="dropdown__button__wrapper">
                            <span>Critical Strike Chance</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    """
    driver = mocker.Mock(page_source=html)
    wait = mocker.Mock()
    wait.until.return_value = True
    mocker.patch("src.gui.importer.d4builds.WebDriverWait", return_value=wait)
    mocker.patch(
        "src.gui.importer.d4builds._get_item_types_from_paperdoll_tooltips",
        return_value={"Bludgeoning Weapon": ItemType.Mace2H},
    )
    save_as_profile_mock = mocker.patch("src.gui.importer.d4builds.save_as_profile", return_value="profile")
    config = ImportConfig(
        url="https://d4builds.gg/builds/whirlwind-barbarian-endgame/?var=4",
        import_uniques=True,
        import_aspect_upgrades=False,
        add_to_profiles=False,
        import_greater_affixes=False,
        require_greater_affixes=False,
        custom_file_name="test",
    )

    import_d4builds(config=config, driver=driver)

    profile = save_as_profile_mock.call_args.kwargs["profile"]
    assert [next(iter(affix_filter.root)) for affix_filter in profile.Affixes] == ["Boots", "BludgeoningWeapon"]
    item_filter = next(iter(profile.Affixes[1].root.values()))
    assert item_filter.itemType == [ItemType.Mace2H]


def test_get_item_types_from_paperdoll_tooltips_reads_visible_tooltip(mocker: MockerFixture) -> None:
    slot_element = mocker.Mock(text="Bludgeoning Weapon")
    name_element = mocker.Mock(text="Heavy Hitting Aspect")
    item_without_slot = mocker.Mock(text="builder gear item child")
    item_without_slot.find_elements.return_value = []
    hover_element = mocker.Mock()
    item = mocker.Mock(text="Heavy Hitting Aspect")

    def find_item_elements(_by: str, value: str) -> list[object]:
        if value == PAPERDOLL_ITEM_SLOT_XPATH:
            return [slot_element]
        if value == PAPERDOLL_ITEM_NAME_XPATH:
            return [name_element]
        if value == PAPERDOLL_ITEM_TOOLTIP_TARGET_XPATH:
            return [hover_element]
        return []

    item.find_elements.side_effect = find_item_elements
    driver = mocker.Mock()
    driver.find_elements.return_value = [item_without_slot, item]
    driver.execute_script.return_value = "2h Mace: 392.7% Overpower Damage"
    actions = mocker.Mock()
    actions.move_to_element.return_value = actions
    mocker.patch("src.gui.importer.d4builds.ActionChains", return_value=actions)
    mocker.patch("src.gui.importer.d4builds.time.sleep")

    item_types = _get_item_types_from_paperdoll_tooltips(driver=driver)

    assert item_types["Bludgeoning Weapon"] == ItemType.Mace2H
    driver.execute_script.assert_any_call(VISIBLE_TOOLTIP_TEXT_SCRIPT, "Heavy Hitting Aspect")
    actions.move_to_element.assert_called_once_with(hover_element)
    actions.perform.assert_called_once()


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
