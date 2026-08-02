import os
from typing import override

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication, QDialog

from src.game_data import SigilRules
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


def test_sigil_lists_keep_canonical_targets_for_mixed_rule_kinds(qapp, mock_ini_loader):
    dungeon_name = _first_dungeon_key()
    affix_name = _first_affix_key()
    model = SigilFilterModel(
        blacklist=[SigilConditionModel(name=dungeon_name)], whitelist=[SigilConditionModel(name=affix_name)]
    )

    tab = SigilsTab(model)
    tab.load()

    assert tab.blacklist_sigils == [dungeon_name]
    assert tab.whitelist_sigils == [affix_name]


def test_remove_sigil_removes_the_selected_canonical_rule(qapp, monkeypatch):
    name = _first_dungeon_key()
    model = SigilFilterModel(blacklist=[SigilConditionModel(name=name)])
    tab = SigilsTab(model)
    tab.load()

    class _AcceptedRemoveDialog(QDialog):
        def __init__(self, *_args, **_kwargs):
            super().__init__()

        @override
        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def get_value(self) -> list[str]:
            return [name]

    monkeypatch.setattr("src.profiles.sigil.tab.RemoveSigil", _AcceptedRemoveDialog)
    tab.remove_sigil(blacklist=True)

    assert model.blacklist == []
    assert tab.blacklist_sigils == []


def test_duplicate_sigil_rename_reverts_without_losing_canonical_identity(qapp, mocker):
    names = [target.name for target in SigilRules.default().targets("dungeon")[:3]]
    model = SigilFilterModel(blacklist=[SigilConditionModel(name=name) for name in names[:2]])
    tab = SigilsTab(model)
    tab.load()
    widget = _layout_widget(tab)
    warning = mocker.patch("src.profiles.sigil.tab.QMessageBox.warning")

    duplicate_index = widget.sigil_name_combo.findText(SigilRules.default().target(names[1]).display)
    widget.sigil_name_combo.setCurrentIndex(duplicate_index)
    assert warning.called
    assert tab.blacklist_sigils == names[:2]
    assert [condition.name for condition in model.blacklist] == names[:2]

    warning.reset_mock()
    replacement_index = widget.sigil_name_combo.findText(SigilRules.default().target(names[2]).display)
    widget.sigil_name_combo.setCurrentIndex(replacement_index)

    assert not warning.called
    assert tab.blacklist_sigils == [names[2], names[1]]
    assert [condition.name for condition in model.blacklist] == [names[2], names[1]]


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


def test_create_sigil_detects_duplicate_canonical_target(qapp, mocker):
    name = _first_dungeon_key()
    display = SigilRules.default().target(name, target_type="dungeon").display
    dialog = CreateSigil([name], [])
    dialog.name_input.setCurrentText(display)
    mock_warning = mocker.patch("src.profiles.sigil.dialogs.QMessageBox.warning")

    dialog.accept()

    assert mock_warning.called
    assert dialog.result() == QDialog.DialogCode.Rejected
