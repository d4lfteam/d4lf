import pytest
from PyQt6.QtWidgets import QApplication

from src.game_data import ItemType
from src.profiles import DynamicItemFilterModel, ItemFilterModel
from src.profiles.affix import AffixesTab, AffixGroupEditor, ItemTypePicker


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


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
    editor.greater_controls.min_greater.setValue(2)
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
