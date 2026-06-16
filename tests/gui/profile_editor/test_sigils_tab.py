import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.config.profile_models import SigilConditionModel, SigilFilterModel
from src.dataloader import Dataloader
from src.gui.profile_editor.sigils_tab import SigilsTab, SigilWidget


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _first_affix_key() -> str:
    data = Dataloader().affix_sigil_dict_all
    return next(iter({**data["minor"], **data["major"], **data["positive"]}))


def _first_dungeon_key() -> str:
    return next(iter(Dataloader().affix_sigil_dict_all["dungeons"]))


def _loaded_tab(name: str) -> SigilsTab:
    model = SigilFilterModel(blacklist=[SigilConditionModel(name=name, condition=[])])
    tab = SigilsTab(model)
    tab.load()  # regression: used to raise KeyError for a top-level affix name
    return tab


def test_global_affix_blacklist_loads_as_affix_kind(qapp, mock_ini_loader):
    tab = _loaded_tab(_first_affix_key())
    widget = tab.blacklist_layout.itemAt(0).widget()
    assert isinstance(widget, SigilWidget)
    assert widget.kind == "affix"


def test_dungeon_blacklist_loads_as_dungeon_kind(qapp, mock_ini_loader):
    tab = _loaded_tab(_first_dungeon_key())
    widget = tab.blacklist_layout.itemAt(0).widget()
    assert isinstance(widget, SigilWidget)
    assert widget.kind == "dungeon"


def test_affix_kind_has_no_condition_list(qapp, mock_ini_loader):
    tab = _loaded_tab(_first_affix_key())
    widget = tab.blacklist_layout.itemAt(0).widget()
    assert not hasattr(widget, "condition_list")


def test_dungeon_kind_has_condition_list(qapp, mock_ini_loader):
    tab = _loaded_tab(_first_dungeon_key())
    widget = tab.blacklist_layout.itemAt(0).widget()
    assert hasattr(widget, "condition_list")
