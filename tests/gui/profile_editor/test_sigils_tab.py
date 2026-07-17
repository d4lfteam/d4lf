import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication

from src.item import SigilRules
from src.profiles import SigilConditionModel, SigilFilterModel
from src.profiles.sigil import CreateSigil, SigilsTab, SigilWidget
from src.profiles.sigil import dialogs as dialog_module


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _first_affix_key() -> str:
    return SigilRules.default().targets("affix")[0].name


def _first_dungeon_key() -> str:
    return SigilRules.default().targets("dungeon")[0].name


def _loaded_tab(name: str) -> SigilsTab:
    model = SigilFilterModel(blacklist=[SigilConditionModel(name=name, condition=[])])
    tab = SigilsTab(model)
    tab.load()  # regression: used to raise KeyError for a top-level affix name
    return tab


def _layout_widget(tab: SigilsTab):
    layout_item = tab.blacklist_layout.itemAt(0)
    assert layout_item is not None
    widget = layout_item.widget()
    assert widget is not None
    return widget


def test_global_affix_blacklist_loads_as_affix_kind(qapp, mock_ini_loader):
    tab = _loaded_tab(_first_affix_key())
    widget = _layout_widget(tab)
    assert isinstance(widget, SigilWidget)
    assert widget.kind == "affix"


def test_dungeon_blacklist_loads_as_dungeon_kind(qapp, mock_ini_loader):
    tab = _loaded_tab(_first_dungeon_key())
    widget = _layout_widget(tab)
    assert isinstance(widget, SigilWidget)
    assert widget.kind == "dungeon"


def test_affix_kind_has_condition_list(qapp, mock_ini_loader):
    tab = _loaded_tab(_first_affix_key())
    widget = _layout_widget(tab)
    assert hasattr(widget, "condition_list")


def test_dungeon_kind_has_condition_list(qapp, mock_ini_loader):
    tab = _loaded_tab(_first_dungeon_key())
    widget = _layout_widget(tab)
    assert hasattr(widget, "condition_list")


def test_create_sigil_remembers_size(qapp, monkeypatch):
    store: dict[str, QSize] = {}

    class FakeSettings:
        def __init__(self, *args, **kwargs):
            pass

        def value(self, key, default=None):
            return store.get(key, default)

        def setValue(self, key, value):  # ruff:ignore[invalid-function-name]
            store[key] = value

    monkeypatch.setattr(dialog_module, "QSettings", FakeSettings)

    dialog = CreateSigil([], [])
    dialog.resize(640, 360)
    dialog.closeEvent(QCloseEvent())

    restored = CreateSigil([], [])
    assert restored.size() == QSize(640, 360)


def test_create_sigil_rejects_unknown_target_kind(qapp, mocker):
    dialog = CreateSigil([], [])
    mocker.patch.object(dialog.kind_input, "currentText", return_value="unknown")

    with pytest.raises(ValueError, match="Unknown sigil rule target type"):
        dialog.get_value()
