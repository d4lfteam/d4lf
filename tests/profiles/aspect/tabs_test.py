import os
from typing import override

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton

from src.profiles.aspect import AspectUpgradesTab


class _AcceptedDialog(QDialog):
    def __init__(self, value: str) -> None:
        super().__init__()
        self._value = value

    @override
    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def get_value(self) -> str:
        return self._value


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _button(tab: AspectUpgradesTab, text: str) -> QPushButton:
    return next(btn for btn in tab.findChildren(QPushButton) if btn.text() == text)


def test_add_aspect_adds_rule_to_list_and_widget(qapp, monkeypatch) -> None:
    monkeypatch.setattr("src.profiles.aspect.tabs.AddAspectUpgrade", lambda *_args, **_kwargs: _AcceptedDialog("new"))

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
