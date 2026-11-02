from typing import TYPE_CHECKING

import pytest
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton

from src.profiles.aspect import AspectUpgradesTab
from src.profiles.aspect.dialogs import AddAspectUpgrade

if TYPE_CHECKING:
    from collections.abc import Callable


def _accept_with(value: str) -> Callable[[AddAspectUpgrade], int]:
    def exec_dialog(dialog: AddAspectUpgrade) -> int:
        dialog.name_input.setCurrentText(value)
        return QDialog.DialogCode.Accepted

    return exec_dialog


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _button(tab: AspectUpgradesTab, text: str) -> QPushButton:
    return next(btn for btn in tab.findChildren(QPushButton) if btn.text() == text)


def test_add_aspect_adds_rule_to_list_and_widget(qapp, monkeypatch) -> None:
    monkeypatch.setattr(AddAspectUpgrade, "exec", _accept_with("new"))

    aspects = ["old"]
    tab = AspectUpgradesTab(aspects)
    tab.load()

    _button(tab, "Add Aspect").click()

    assert aspects == ["old", "new"]
    assert tab.list_widget.count() == 2
    item = tab.list_widget.item(1)
    assert item is not None
    assert item.text() == "new"


def test_remove_selected_with_no_selection_shows_warning_and_does_not_crash(qapp, monkeypatch) -> None:
    warnings: list[tuple[str, str]] = []

    def _warning(parent, title: str, message: str) -> None:
        warnings.append((title, message))

    monkeypatch.setattr(QMessageBox, "warning", _warning)

    aspects = ["old"]
    tab = AspectUpgradesTab(aspects)
    tab.load()

    _button(tab, "Remove Selected").click()

    assert aspects == ["old"]
    assert warnings == [("Warning", "Select at least one rule to remove.")]
