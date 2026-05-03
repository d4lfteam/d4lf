import os
import typing

import pytest

from src.dataloader import Dataloader
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.maxroll import _find_item_type, import_maxroll
from src.item.data.item_type import ItemType

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture
IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

URLS = [
    "https://maxroll.gg/d4/build-guides/auradin-guide",
    "https://maxroll.gg/d4/build-guides/blessed-hammer-paladin-guide",
    "https://maxroll.gg/d4/build-guides/double-swing-barbarian-guide",
    "https://maxroll.gg/d4/build-guides/evade-spiritborn-build-guide",
    "https://maxroll.gg/d4/build-guides/frozen-orb-sorcerer-guide",
    "https://maxroll.gg/d4/build-guides/minion-necromancer-guide",
    "https://maxroll.gg/d4/build-guides/quill-volley-spiritborn-guide",
    "https://maxroll.gg/d4/build-guides/shield-of-retribution-paladin-guide",
    "https://maxroll.gg/d4/build-guides/touch-of-death-spiritborn-guide",
]


@pytest.mark.parametrize("url", URLS)
@pytest.mark.requests
@pytest.mark.skipif(not IN_GITHUB_ACTIONS, reason="Importer tests are skipped if not run from Github Actions")
def test_import_maxroll(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
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
    import_maxroll(config=config)


def test_find_item_type_uses_fix_weapon_type_with_slot_context() -> None:
    assert (
        _find_item_type(mapping_data={"item-1": {"type": "2H Sword"}}, value="item-1", class_name="Barbarian")
        == ItemType.Sword2H
    )


def test_find_item_type_uses_fix_offhand_type_with_slot_and_class_context() -> None:
    assert (
        _find_item_type(mapping_data={"item-1": {"type": "FocusBookOffHand"}}, value="item-1", class_name="Sorcerer")
        == ItemType.Focus
    )


def test_find_item_type_uses_fix_offhand_type_when_item_type_implies_offhand() -> None:
    assert (
        _find_item_type(mapping_data={"item-1": {"type": "1HFocus"}}, value="item-1", class_name="Sorcerer")
        == ItemType.Focus
    )
