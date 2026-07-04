import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton

from src.gui.models.rule_list_tab import RuleListTab


class _AcceptedDialog(QDialog):
    def __init__(self, value: str):
        super().__init__()
        self._value = value

    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def get_value(self) -> str:
        return self._value


class _StubRuleListTab(RuleListTab[str]):
    def description_text(self) -> str:
        return "Stub description"

    def add_actions(self):
        return [("Add Item", lambda: _AcceptedDialog("beta"))]

    def on_add_accepted(self, dialog: QDialog) -> str:
        item = dialog.get_value()
        self.items.append(item)
        return item

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
    assert tab.list_widget.item(1).text() == "Item: beta"


def test_remove_selected_removes_rows_from_backing_list_and_widget(qapp):
    items = ["alpha", "beta", "gamma"]
    tab = _StubRuleListTab(items)
    tab.load()

    tab.list_widget.item(0).setSelected(True)
    tab.list_widget.item(2).setSelected(True)
    _button(tab, "Remove Selected").click()

    assert items == ["beta"]
    assert tab.list_widget.count() == 1
    assert tab.list_widget.item(0).text() == "Item: beta"


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
