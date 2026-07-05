import os

import pytest
from PyQt6.QtWidgets import QApplication, QWidget

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.config.profile_models import AffixFilterModel, CharmFilterModel, SealFilterModel
from src.gui.profile_editor.affixes_tab import AffixWidget


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class MockGroupEditor(QWidget):
    """Mock group editor to act as a parent with a config attribute."""

    def __init__(self, config):
        super().__init__()
        self.config = config

    def update_greater_count_label(self):
        pass

    def sync_min_greater_from_checkboxes(self):
        pass


def test_affix_widget_parent_config(qapp, mock_ini_loader):
    # Test that both SealFilterModel and CharmFilterModel are recognized as parent configs
    seal_config = SealFilterModel(affix_pool=[])
    charm_config = CharmFilterModel(affix_pool=[])

    affix = AffixFilterModel(name="movement_speed", value=None)

    parent_seal = MockGroupEditor(seal_config)
    widget_seal = AffixWidget(affix, parent=parent_seal)
    assert widget_seal.get_parent_config() is seal_config

    parent_charm = MockGroupEditor(charm_config)
    widget_charm = AffixWidget(affix, parent=parent_charm)
    assert widget_charm.get_parent_config() is charm_config


def test_affix_widget_clears_on_empty_filter(qapp, mock_ini_loader):
    # Test that if name_combo has no items, update_name clears self.affix.name
    affix = AffixFilterModel(name="movement_speed", value=None)
    charm_config = CharmFilterModel(affix_pool=[])

    parent = MockGroupEditor(charm_config)
    widget = AffixWidget(affix, parent=parent)

    # Initially it should match movement_speed
    assert widget.affix.name == "movement_speed"

    # Set filtered_affixes to empty to simulate a set change filtering out all options
    widget.filtered_affixes = {}
    widget.name_combo.clear()

    # Call update_name with empty string
    widget.update_name("")

    # It must clear the name
    assert not widget.affix.name
