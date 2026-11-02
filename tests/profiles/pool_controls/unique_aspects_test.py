import pytest
from PyQt6.QtWidgets import QApplication

from src.game_data import GameCatalog
from src.profiles import AspectUniqueFilterModel, CharmFilterModel, ItemFilterModel, SealFilterModel
from src.profiles.pool_controls import UniqueAspectSection


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_loads_existing_aspects_on_first_expansion(qapp, mock_ini_loader) -> None:
    aspect_name = next(iter(GameCatalog().aspect_unique_dict))
    config = ItemFilterModel(unique_aspect=[AspectUniqueFilterModel(name=aspect_name)])
    section = UniqueAspectSection(config)

    assert section.header.name == f"Unique Aspects - {aspect_name}"
    assert section.aspect_list.count() == 0
    section.expand()
    assert section.aspect_list.count() == 1


def test_add_uses_prefix_and_remove_updates_config(qapp, mock_ini_loader) -> None:
    config = SealFilterModel()
    section = UniqueAspectSection(config, aspect_prefix="seal_of")

    section.add_aspect()
    assert len(config.unique_aspect) == 1
    assert config.unique_aspect[0].name.startswith("seal_of")
    assert section.header.name == f"Unique Aspects - {config.unique_aspect[0].name}"

    section.aspect_list.setCurrentRow(0)
    section.remove_selected_aspects()
    assert config.unique_aspect == []
    assert section.header.name == "Unique Aspects - None"


def test_add_is_blocked_for_charms_with_sets(qapp, mock_ini_loader, mocker) -> None:
    warning = mocker.patch("src.profiles.pool_controls.unique_aspects.QMessageBox.warning")
    config = CharmFilterModel(set=["sescherons_fury"])

    UniqueAspectSection(config, aspect_prefix="charm_of").add_aspect()

    assert warning.called
    assert config.unique_aspect == []
