import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QCheckBox

from src.desktop.widgets import CheckmarkCheckBox, set_accent_color


def test_checkmark_checkbox_is_a_qt_checkbox(qapp: QApplication) -> None:
    checkbox = CheckmarkCheckBox("Keep")
    checkbox.setChecked(True)

    assert isinstance(checkbox, QCheckBox)
    assert checkbox.isChecked()

    set_accent_color("#56B4E9")
    checkbox.update()
    checkbox.close()


def test_qapp(qapp: QApplication) -> None:
    assert QApplication.instance() is qapp


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if isinstance(app, QApplication):
        return app
    return QApplication([])
