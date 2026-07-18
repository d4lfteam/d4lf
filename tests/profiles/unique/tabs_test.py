import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication

from src.profiles import GlobalUniqueModel
from src.profiles.unique import UniquesTab, UniqueWidget


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_unique_widget_updates_all_thresholds(qapp):
    model = GlobalUniqueModel()
    widget = UniqueWidget(model)

    widget.profile_alias.setText("  build alias  ")
    widget.min_power.setValue(800)
    widget.min_greater.setValue(3)
    widget.min_percent.setValue(75)

    assert model.profile_alias == "build alias"
    assert model.min_power == 800
    assert model.min_greater_affix_count == 3
    assert model.min_percent_of_aspect == 75


def test_uniques_tab_adds_and_removes_rules(qapp):
    models = [GlobalUniqueModel(profile_alias="existing")]
    tab = UniquesTab(models)
    tab.load()

    tab.add_item()
    assert len(models) == 2
    assert tab.tab_widget.tabText(1) == "Unique Rule 1"

    tab.close_tab(0)
    assert len(models) == 1
    assert tab.tab_widget.tabText(0) == "Unique Rule 0"
