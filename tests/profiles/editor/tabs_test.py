import importlib
from typing import override

import pytest
from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QWidget

from src.profiles.editor import SelectToDeleteDialog, tabs
from src.profiles.editor.tabs import TabGroupWidget


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    return app if isinstance(app, QApplication) else QApplication([])


class NamedTabs(TabGroupWidget[str]):
    @override
    def create_editor(self, model: str) -> QWidget:
        return QLabel(model)

    @override
    def tab_label(self, model: str, index: int) -> str:
        return model.split("#", maxsplit=1)[0]


def fake_dialog_selecting(selected: list[int]) -> type[SelectToDeleteDialog[int]]:
    class FakeSelectToDeleteDialog(SelectToDeleteDialog[int]):
        @override
        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        @override
        def get_value(self) -> list[int]:
            return selected

    return FakeSelectToDeleteDialog


def build(models: list[str]) -> NamedTabs:
    widget = NamedTabs(models)
    widget.load()
    return widget


def tab_texts(widget: NamedTabs) -> list[str]:
    return [widget.tab_widget.tabText(i) for i in range(widget.tab_widget.count())]


def test_tabs_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.tabs")
    assert hasattr(module, "TabGroupWidget")


def test_remove_item_with_duplicate_names_removes_only_selected(qapp, monkeypatch: pytest.MonkeyPatch) -> None:
    widget = build(["Same#a", "Same#b"])
    monkeypatch.setattr(tabs, "SelectToDeleteDialog", fake_dialog_selecting([1]))

    widget.remove_item()

    assert widget.models == ["Same#a"]
    assert tab_texts(widget) == ["Same"]
    editor = widget.tab_widget.widget(0)
    assert isinstance(editor, QLabel)
    assert editor.text() == "Same#a"


def test_remove_item_non_adjacent_keeps_middle(qapp, monkeypatch: pytest.MonkeyPatch) -> None:
    widget = build(["First", "Middle", "Last"])
    monkeypatch.setattr(tabs, "SelectToDeleteDialog", fake_dialog_selecting([0, 2]))

    widget.remove_item()

    assert widget.models == ["Middle"]
    assert tab_texts(widget) == ["Middle"]
