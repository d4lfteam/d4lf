import os

import pytest
from PyQt6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.game_data import ItemType
from src.profiles.affix.dialogs import CreateItem


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("name", ["", "sword"])
def test_create_item_rejects_empty_or_existing_names(qapp, mock_ini_loader, mocker, name) -> None:
    warning = mocker.patch("src.profiles.affix.dialogs.QMessageBox.warning")
    dialog = CreateItem(["sword"])
    dialog.name_input.setText(name)

    dialog.accept()

    warning.assert_called_once()
    assert dialog.result() != CreateItem.DialogCode.Accepted


def test_create_item_builds_default_amulet_filter(qapp, mock_ini_loader) -> None:
    dialog = CreateItem(["sword"])
    dialog.name_input.setText("amulet")

    dialog.accept()
    model = dialog.get_value()

    assert dialog.result() == CreateItem.DialogCode.Accepted
    config = model.root["amulet"]
    assert config.item_type == [ItemType.Amulet]
    assert config.min_power == 100
    assert config.affix_pool[0].min_count == 2
