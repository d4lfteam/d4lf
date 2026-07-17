import os
from typing import override

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton

from src.profiles.editor import RuleListTab


class _AcceptedDialog(QDialog):
    def __init__(self, value: str):
        super().__init__()
        self._value = value

    @override
    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def get_value(self) -> str:
        return self._value


class _StubRuleListTab(RuleListTab[str]):
    @override
    def description_text(self) -> str:
        return "Stub description"

    @override
    def add_actions(self):
        return [("Add Item", lambda: _AcceptedDialog("beta"))]

    @override
    def on_add_accepted(self, dialog: QDialog) -> str:
        if not isinstance(dialog, _AcceptedDialog):
            msg = "unexpected dialog type"
            raise TypeError(msg)
        item = dialog.get_value()
        self.items.append(item)
        return item

    @override
    def to_display_text(self, item: str) -> str:
        return f"Item: {item}"


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _button(tab: _StubRuleListTab, label: str) -> QPushButton:
    return next(btn for btn in tab.findChildren(QPushButton) if btn.text() == label)


def test_add_action_appends_to_backing_list_and_list_widget(qapp):
    items = ["alpha"]
    tab = _StubRuleListTab(items)
    tab.load()

    _button(tab, "Add Item").click()

    assert items == ["alpha", "beta"]
    assert tab.list_widget.count() == 2
    item = tab.list_widget.item(1)
    assert item is not None
    assert item.text() == "Item: beta"


def test_remove_selected_removes_rows_from_backing_list_and_widget(qapp):
    items = ["alpha", "beta", "gamma"]
    tab = _StubRuleListTab(items)
    tab.load()

    first_item = tab.list_widget.item(0)
    third_item = tab.list_widget.item(2)
    assert first_item is not None
    assert third_item is not None
    first_item.setSelected(True)
    third_item.setSelected(True)
    _button(tab, "Remove Selected").click()

    assert items == ["beta"]
    assert tab.list_widget.count() == 1
    item = tab.list_widget.item(0)
    assert item is not None
    assert item.text() == "Item: beta"


def test_remove_selected_warns_when_nothing_is_selected(qapp, monkeypatch):
    items = ["alpha"]
    tab = _StubRuleListTab(items)
    tab.load()
    warnings: list[tuple[str, str]] = []

    def _warning(parent, title: str, message: str):
        warnings.append((title, message))

    monkeypatch.setattr(QMessageBox, "warning", _warning)

    _button(tab, "Remove Selected").click()

    assert items == ["alpha"]
    assert tab.list_widget.count() == 1
    assert warnings == [("Warning", "Select at least one rule to remove.")]
