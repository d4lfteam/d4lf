import importlib
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.game_data import GameCatalog, ItemType
from src.profiles.affix.picker import ItemTypePicker


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_picker_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.affix.picker")
    assert hasattr(module, "ItemTypePicker")


def test_picker_uses_catalog_labels(qapp, monkeypatch) -> None:
    catalog = GameCatalog()
    monkeypatch.setattr(catalog, "item_types_dict", {**catalog.item_types_dict, "Helm": "Casque"})

    picker = ItemTypePicker(None, [ItemType.Helm], [])

    assert picker.checkboxes[ItemType.Helm].text() == "Casque"
    picker.close()
