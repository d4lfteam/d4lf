import importlib

import pytest
from PyQt6.QtWidgets import QApplication

from src.profiles.editor import SelectToDeleteDialog


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    return app if isinstance(app, QApplication) else QApplication([])


def test_pickers_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.pickers")
    assert hasattr(module, "RarityPicker")


def test_select_to_delete_dialog_returns_checked_values(qapp) -> None:
    dialog = SelectToDeleteDialog("Delete Things", "Things", "Select:", [("a", 10), ("b", 20), ("c", 30)])

    dialog.checkboxes[0][0].setChecked(True)
    dialog.checkboxes[2][0].setChecked(True)

    assert dialog.windowTitle() == "Delete Things"
    assert dialog.get_value() == [10, 30]
