import os
from typing import override

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog, QPushButton

from src.config.profile_models import ItemRarity, TributeFilterModel
from src.gui.models.dialog import CreateTribute
from src.gui.profile_editor.profile_editor import _to_editor_tribute_filter
from src.gui.profile_editor.tributes_tab import TributesTab


class _AcceptedDialog(QDialog):
    def __init__(self, value: TributeFilterModel):
        super().__init__()
        self._value = value

    @override
    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def get_value(self) -> TributeFilterModel:
        return self._value


class _AcceptedRarityPicker(QDialog):
    def __init__(self, selected_rarities: list[ItemRarity]):
        super().__init__()
        self._selected_rarities = selected_rarities

    @override
    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def get_selected_rarities(self) -> list[ItemRarity]:
        return self._selected_rarities


class _FakeLoader:
    tribute_dict = {"tribute_of_test": "Tribute Of Test"}


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _button(tab: TributesTab, text: str) -> QPushButton:
    return next(btn for btn in tab.findChildren(QPushButton) if btn.text() == text)


def test_add_tribute_adds_name_rule_with_expected_display_text(qapp, monkeypatch):
    monkeypatch.setattr("src.gui.profile_editor.tributes_tab.Dataloader", _FakeLoader)
    monkeypatch.setattr(
        "src.gui.profile_editor.tributes_tab.CreateTribute",
        lambda *_args, **_kwargs: _AcceptedDialog(
            TributeFilterModel.model_construct(name=["tribute_of_test"], rarities=[])
        ),
    )

    tributes = TributeFilterModel()
    tab = TributesTab(tributes)
    tab.load()

    _button(tab, "Add Tribute").click()

    assert tributes.name == ["tribute_of_test"]
    item = tab.list_widget.item(0)
    assert item is not None
    assert item.text() == "Tribute: Tribute Of Test"


def test_edit_rarities_updates_summary_and_model(qapp, monkeypatch):
    monkeypatch.setattr("src.gui.profile_editor.tributes_tab.Dataloader", _FakeLoader)
    monkeypatch.setattr(
        "src.gui.profile_editor.tributes_tab.RarityPicker",
        lambda *_args, **_kwargs: _AcceptedRarityPicker([ItemRarity.Rare]),
    )

    tributes = TributeFilterModel()
    tab = TributesTab(tributes)
    tab.load()

    tab.edit_rarities()

    assert tributes.rarities == [ItemRarity.Rare]
    assert tab.rarity_line_edit.text() == "rare"


def test_to_editor_tribute_filter_returns_empty_model_for_none():
    assert _to_editor_tribute_filter(None) == TributeFilterModel()


def test_to_editor_tribute_filter_returns_model_unchanged():
    model = TributeFilterModel.model_construct(name=["tribute_of_harmony"], rarities=[ItemRarity.Rare])
    assert _to_editor_tribute_filter(model) is model


def test_create_tribute_rejects_unknown_display_name(qapp):
    dialog = CreateTribute([])
    dialog.name_input.setCurrentText("Unknown Tribute")

    with pytest.raises(ValueError, match="Select a valid tribute"):
        dialog.get_value()
