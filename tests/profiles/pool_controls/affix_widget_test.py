import operator

import pytest
from PyQt6.QtWidgets import QApplication, QWidget

from src.profiles import AffixFilterModel, CharmFilterModel, SealFilterModel
from src.profiles.pool_controls import AffixWidget


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class MockGroupEditor(QWidget):
    """Mock group editor to act as a parent with a config attribute."""

    def __init__(self, config) -> None:
        super().__init__()
        self.config = config

    def refresh_greater_count(self) -> None:
        pass


def test_affix_widget_parent_config(qapp, mock_ini_loader) -> None:
    # Test that only SealFilterModel is recognized as a parent seal config
    seal_config = SealFilterModel(affix_pool=[])
    charm_config = CharmFilterModel(affix_pool=[])

    affix = AffixFilterModel(name="movement_speed", value=None)

    parent_seal = MockGroupEditor(seal_config)
    widget_seal = AffixWidget(affix, parent=parent_seal)
    assert widget_seal.get_parent_seal_config() is seal_config

    parent_charm = MockGroupEditor(charm_config)
    widget_charm = AffixWidget(affix, parent=parent_charm)
    assert widget_charm.get_parent_seal_config() is None


def test_affix_widget_clears_on_empty_filter(qapp, mock_ini_loader) -> None:
    # Test that if name_combo has no items, update_name clears self.affix.name (for seals)
    affix = AffixFilterModel(name="adept_action_damage_reduction_while_moving", value=None)
    seal_config = SealFilterModel(affix_pool=[])

    parent = MockGroupEditor(seal_config)
    widget = AffixWidget(affix, parent=parent)

    # Initially it should match adept_action_damage_reduction_while_moving
    assert widget.affix.name == "adept_action_damage_reduction_while_moving"

    # Set filtered_affixes to empty to simulate a set change filtering out all options
    widget.filtered_affixes = {}
    widget.name_combo.clear()

    # Call update_name with empty string
    widget.update_name("")

    # It must clear the name
    assert operator.not_(widget.affix.name)
