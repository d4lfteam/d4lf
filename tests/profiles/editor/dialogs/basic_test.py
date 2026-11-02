import importlib

import pytest
from PyQt6.QtWidgets import QApplication, QDialog, QDialogButtonBox

from src.profiles.editor.dialogs import MinPowerDialog


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    return app if isinstance(app, QApplication) else QApplication([])


def test_dialogs_basic_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.dialogs.basic")
    assert hasattr(module, "MinPowerDialog")


def test_ok_cancel_buttons_wire_accept_and_reject(qapp: QApplication) -> None:
    dialog = MinPowerDialog()
    button_box = dialog.findChild(QDialogButtonBox)
    assert button_box is not None

    ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
    assert ok_button is not None
    ok_button.click()
    assert dialog.result() == QDialog.DialogCode.Accepted

    cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)
    assert cancel_button is not None
    cancel_button.click()
    assert dialog.result() == QDialog.DialogCode.Rejected
