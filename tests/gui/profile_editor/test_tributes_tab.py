import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog, QPushButton

from src.config.profile_models import ItemRarity, TributeFilterModel
from src.gui.profile_editor.tributes_tab import TributesTab


class _AcceptedDialog(QDialog):
    def __init__(self, value: TributeFilterModel):
        super().__init__()
        self._value = value

    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def get_value(self) -> TributeFilterModel:
        return self._value


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
    assert tab.list_widget.item(0).text() == "Tribute: Tribute Of Test"


def test_add_rarity_adds_rarity_rule_with_expected_display_text(qapp, monkeypatch):
    monkeypatch.setattr("src.gui.profile_editor.tributes_tab.Dataloader", _FakeLoader)
    monkeypatch.setattr(
        "src.gui.profile_editor.tributes_tab.AddTributeRarity",
        lambda *_args, **_kwargs: _AcceptedDialog(
            TributeFilterModel.model_construct(name=[], rarities=[ItemRarity.Rare])
        ),
    )

    tributes = TributeFilterModel()
    tab = TributesTab(tributes)
    tab.load()

    _button(tab, "Add Rarity").click()

    assert tributes.rarities == [ItemRarity.Rare]
    assert tab.list_widget.item(0).text() == "Rarities: Rare"
