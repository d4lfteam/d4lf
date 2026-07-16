import os

import pytest
from PyQt6.QtWidgets import QApplication, QDialog

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.gui.profile_editor.charms_seals_group_tab import CharmGroupEditor, CharmsTab, SealGroupEditor, SealsTab
from src.item.data.rarity import ItemRarity
from src.profiles import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    CharmFilterModel,
    DynamicCharmFilterModel,
    DynamicSealFilterModel,
    SealFilterModel,
)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _create_mock_charm_model(name: str) -> DynamicCharmFilterModel:
    default_affix = AffixFilterModel(name="movement_speed", value=None)
    default_pool = AffixFilterCountModel(count=[default_affix], min_count=1, max_count=3)
    config = CharmFilterModel(affix_pool=[default_pool])
    return DynamicCharmFilterModel(root={name: config})


def _create_mock_seal_model(name: str) -> DynamicSealFilterModel:
    default_affix = AffixFilterModel(name="all_stats", value=None)
    default_pool = AffixFilterCountModel(count=[default_affix], min_count=1, max_count=3)
    config = SealFilterModel(affix_pool=[default_pool])
    return DynamicSealFilterModel(root={name: config})


def test_charms_tab_close_tab_safely(qapp, mock_ini_loader):
    # Create models list, including a multi-key model (representing grouped YAML entries)
    default_affix = AffixFilterModel(name="movement_speed", value=None)
    default_pool = AffixFilterCountModel(count=[default_affix], min_count=1, max_count=3)
    config1 = CharmFilterModel(affix_pool=[default_pool])
    config2 = CharmFilterModel(affix_pool=[default_pool], min_greater_affix_count=2)

    # Initial state with a grouped entry
    charms_list = [
        DynamicCharmFilterModel(root={"Charm1": config1, "Charm2": config2}),
        _create_mock_charm_model("Charm3"),
    ]

    tab = CharmsTab(charms_list)
    tab.load()

    # The models list should be normalized to 3 separate single-key models
    assert len(tab.models) == 3
    assert [tab.tab_widget.tabText(i) for i in range(tab.tab_widget.count())] == ["Charm1", "Charm2", "Charm3"]
    assert tab.tab_widget.count() == 3

    # Close Charm2 (index 1)
    tab.close_tab(1)

    # Check state after deletion
    assert [tab.tab_widget.tabText(i) for i in range(tab.tab_widget.count())] == ["Charm1", "Charm3"]
    assert tab.tab_widget.count() == 2
    assert len(tab.models) == 2
    # Ensure remaining models have correct keys
    assert "Charm1" in tab.models[0].root
    assert "Charm3" in tab.models[1].root


def test_seals_tab_close_tab_safely(qapp, mock_ini_loader):
    default_affix = AffixFilterModel(name="all_stats", value=None)
    default_pool = AffixFilterCountModel(count=[default_affix], min_count=1, max_count=3)
    config1 = SealFilterModel(affix_pool=[default_pool])
    config2 = SealFilterModel(affix_pool=[default_pool], min_greater_affix_count=2)

    seals_list = [DynamicSealFilterModel(root={"Seal1": config1, "Seal2": config2}), _create_mock_seal_model("Seal3")]

    tab = SealsTab(seals_list)
    tab.load()

    assert len(tab.models) == 3
    assert [tab.tab_widget.tabText(i) for i in range(tab.tab_widget.count())] == ["Seal1", "Seal2", "Seal3"]

    # Close Seal2 (index 1)
    tab.close_tab(1)

    assert [tab.tab_widget.tabText(i) for i in range(tab.tab_widget.count())] == ["Seal1", "Seal3"]
    assert tab.tab_widget.count() == 2
    assert len(tab.models) == 2
    assert "Seal1" in tab.models[0].root
    assert "Seal3" in tab.models[1].root


def test_charms_seals_qsettings_namespacing(qapp, mock_ini_loader):
    charm_model = _create_mock_charm_model("MyBuild")
    seal_model = _create_mock_seal_model("MyBuild")

    charm_editor = CharmGroupEditor(charm_model)
    seal_editor = SealGroupEditor(seal_model)

    assert charm_editor.type_prefix == "charm"
    assert seal_editor.type_prefix == "seal"
    assert charm_editor.item_name == "MyBuild"
    assert seal_editor.item_name == "MyBuild"


def test_charms_ui_set_aspect_mutual_exclusion(qapp, mock_ini_loader, mocker):
    mock_warning = mocker.patch("PyQt6.QtWidgets.QMessageBox.warning")

    charm_model = _create_mock_charm_model("MyBuild")
    charm_editor = CharmGroupEditor(charm_model)

    # 1. Set has value, try to add unique aspect
    charm_editor.config.set = ["Sescherons Fury"]
    charm_editor.config.unique_aspect = []
    charm_editor.add_unique_aspect()
    assert mock_warning.called
    assert len(charm_editor.config.unique_aspect) == 0

    # Reset mock
    mock_warning.reset_mock()

    # 2. Unique aspect has value, try to edit sets
    charm_editor.config.set = []
    charm_editor.config.unique_aspect = [AspectUniqueFilterModel(name="seal_of_the_diamond_mind", value=None)]
    charm_editor.edit_sets()
    assert mock_warning.called
    assert len(charm_editor.config.set) == 0


def test_charms_ui_edit_rarities(qapp, mock_ini_loader, mocker):
    charm_model = _create_mock_charm_model("MyBuild")
    charm_editor = CharmGroupEditor(charm_model)

    # Mock RarityPicker dialog execution
    mock_exec = mocker.patch("src.gui.profile_editor.charms_seals_group_tab.RarityPicker.exec", return_value=1)
    mock_get_selected_rarities = mocker.patch(
        "src.gui.profile_editor.charms_seals_group_tab.RarityPicker.get_selected_rarities",
        return_value=[ItemRarity.Rare, ItemRarity.Legendary],
    )

    # Initial rarities
    charm_editor.config.rarities = []

    # Run edit_rarities
    charm_editor.edit_rarities()

    assert mock_exec.called
    assert mock_get_selected_rarities.called
    assert charm_editor.config.rarities == [ItemRarity.Rare, ItemRarity.Legendary]


def test_charms_ui_edit_sets_updates_model(qapp, mock_ini_loader, monkeypatch):
    charm_model = _create_mock_charm_model("MyBuild")
    charm_editor = CharmGroupEditor(charm_model)

    class FakeSetPicker:
        def __init__(self, parent, selected_sets):
            self.parent = parent
            self.selected_sets = selected_sets

        def exec(self):
            return QDialog.DialogCode.Accepted

        def get_selected_sets(self):
            return ["sescherons_fury", "demonbinder"]

    monkeypatch.setattr("src.gui.profile_editor.charms_seals_group_tab.SetPicker", FakeSetPicker)

    charm_editor.edit_sets()

    assert charm_editor.config.set == ["sescherons_fury", "demonbinder"]


def test_charm_group_editor_rejects_multi_key_dynamic_model(qapp, mock_ini_loader):
    default_affix = AffixFilterModel(name="movement_speed", value=None)
    default_pool = AffixFilterCountModel(count=[default_affix], min_count=1, max_count=3)
    config1 = CharmFilterModel(affix_pool=[default_pool])
    config2 = CharmFilterModel(affix_pool=[default_pool], min_greater_affix_count=2)
    multi_key_model = DynamicCharmFilterModel(root={"Charm1": config1, "Charm2": config2})

    with pytest.raises(ValueError, match="single-key"):
        CharmGroupEditor(multi_key_model)
