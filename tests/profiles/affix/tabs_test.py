import os

import pytest
from PyQt6.QtWidgets import QApplication, QWidget

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.game_data import GameCatalog, ItemType
from src.profiles import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    CharmFilterModel,
    DynamicItemFilterModel,
    ItemFilterModel,
    SealFilterModel,
)
from src.profiles.affix import (
    AffixesTab,
    AffixGroupEditor,
    AffixPoolWidget,
    AffixWidget,
    ItemTypePicker,
    UniqueAspectWidget,
)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class MockGroupEditor(QWidget):
    """Mock group editor to act as a parent with a config attribute."""

    def __init__(self, config) -> None:
        super().__init__()
        self.config = config

    def update_greater_count_label(self) -> None:
        pass

    def sync_min_greater_from_checkboxes(self) -> None:
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
    assert not widget.affix.name


def test_affix_pool_add_and_remove_lifecycle(qapp, mock_ini_loader) -> None:
    affix = AffixFilterModel(name="movement_speed")
    pool = AffixFilterCountModel(count=[affix], min_count=1, max_count=3)
    widget = AffixPoolWidget(pool)

    assert widget.affix_list.count() == 1
    widget.add_affix()
    assert len(pool.count) == 2
    assert widget.affix_list.count() == 2

    item = widget.affix_list.item(0)
    assert item is not None
    item.setSelected(True)
    widget.remove_selected(widget.affix_list)
    assert len(pool.count) == 1
    assert widget.affix_list.count() == 1


def test_item_type_picker_selection_and_clear(qapp, mock_ini_loader) -> None:
    item_types = [ItemType.Sword, ItemType.Helm]
    picker = ItemTypePicker(None, item_types, [ItemType.Sword])

    assert picker.get_selected_item_types() == [ItemType.Sword]
    picker.checkboxes[ItemType.Helm].setChecked(True)
    assert set(picker.get_selected_item_types()) == set(item_types)
    picker.clear_selection()
    assert picker.get_selected_item_types() == []


def test_affix_group_editor_updates_power_and_greater_count(qapp, mock_ini_loader) -> None:
    config = ItemFilterModel()
    editor = AffixGroupEditor(DynamicItemFilterModel(root={"sword": config}))

    editor.min_power.setValue(850)
    editor.min_greater.setValue(2)
    assert config.min_power == 850
    assert config.min_greater_affix_count == 2


def test_affixes_tab_splits_grouped_models_and_keeps_deletion_aligned(qapp, mock_ini_loader) -> None:
    sword_config = ItemFilterModel(min_power=850, min_greater_affix_count=1)
    helm_config = ItemFilterModel(min_power=900, min_greater_affix_count=2)
    grouped_model = DynamicItemFilterModel(root={"sword": sword_config, "helm": helm_config})
    affixes = [grouped_model]

    tab = AffixesTab(affixes)
    tab.load()

    assert [tab.tab_widget.tabText(i) for i in range(tab.tab_widget.count())] == ["sword", "helm"]
    assert len(affixes) == 2
    sword_editor = tab.tab_widget.widget(0)
    helm_editor = tab.tab_widget.widget(1)
    assert isinstance(sword_editor, AffixGroupEditor)
    assert isinstance(helm_editor, AffixGroupEditor)
    assert sword_editor.item_name == "sword"
    assert sword_editor.config is sword_config
    assert sword_editor.min_power.value() == 850
    assert helm_editor.item_name == "helm"
    assert helm_editor.config is helm_config
    assert helm_editor.min_power.value() == 900

    tab.close_tab(0)

    assert [tab.tab_widget.tabText(i) for i in range(tab.tab_widget.count())] == ["helm"]
    assert len(affixes) == 1
    assert affixes[0].root == {"helm": helm_config}


def test_affixes_tab_preserves_models_and_disables_editor_on_duplicate_name(qapp, mock_ini_loader, mocker) -> None:
    sword_config = ItemFilterModel(min_power=850)
    helm_config = ItemFilterModel(min_power=900)
    duplicate_sword_config = ItemFilterModel(min_power=950)
    first_model = DynamicItemFilterModel(root={"sword": sword_config})
    second_model = DynamicItemFilterModel(root={"helm": helm_config, "sword": duplicate_sword_config})
    affixes = [first_model, second_model]
    warning = mocker.patch("src.profiles.affix.tabs.QMessageBox.warning")

    tab = AffixesTab(affixes)
    tab.load()

    warning.assert_called_once()
    assert affixes == [first_model, second_model]
    assert affixes[0] is first_model
    assert affixes[1] is second_model
    assert first_model.root == {"sword": sword_config}
    assert second_model.root == {"helm": helm_config, "sword": duplicate_sword_config}
    assert tab.tab_widget.count() == 0
    assert not tab.tab_widget.isEnabled()
    assert not tab.toolbar.isEnabled()
    warning_label = tab.warning_label
    assert warning_label is not None
    assert "disabled" in warning_label.text().lower()


def test_unique_aspect_widget_value_and_percent_are_mutually_exclusive(qapp, mock_ini_loader) -> None:
    aspect_name = next(iter(GameCatalog().aspect_unique_dict))
    model = AspectUniqueFilterModel(name=aspect_name, value=1.5)
    widget = UniqueAspectWidget(model)

    widget.mode_combo.setCurrentText("Min %")
    widget.value_edit.setText("25")
    assert model.min_percent_of_aspect == 25
    assert model.value is None

    widget.mode_combo.setCurrentText("Value")
    widget.value_edit.setText("2.5")
    assert model.value == pytest.approx(2.5)
    assert model.min_percent_of_aspect == 0
