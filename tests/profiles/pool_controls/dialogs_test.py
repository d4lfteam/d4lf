import os

import pytest
from PyQt6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.profiles.pool_controls import DeleteAffixPool


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_delete_affix_pool_returns_checked_pool_names(qapp) -> None:
    dialog = DeleteAffixPool(3, inherent=True)

    dialog.checkbox_list[0].setChecked(True)
    dialog.checkbox_list[2].setChecked(True)

    assert dialog.windowTitle() == "Delete Inherent Pool"
    assert dialog.get_value() == ["Count 0", "Count 2"]
