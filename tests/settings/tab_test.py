import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QLineEdit, QMessageBox

from src.settings import SettingsCategory
from src.settings.tab import ConfigTab
from src.settings.widgets import QChestTabWidget


@pytest.fixture
def tab(qapp, isolated_ini_loader):
    config_tab = ConfigTab()
    yield config_tab
    config_tab.close()


def test_config_tab_can_be_constructed(tab: ConfigTab) -> None:
    assert tab.nav_list.count() > 0


def test_loot_filter_override_switches_explain_mythic_behavior(tab: ConfigTab) -> None:
    for key in ("equipment", "sigils", "tributes", "seals", "charms"):
        tooltip = tab.rows["general", f"filter_{key}"].control.toolTip()
        assert "all" in tooltip
        assert "skipped" in tooltip
        assert "including Mythic" in tooltip
        assert "always kept" in tooltip


def test_save_rejects_invalid_value_and_restores_control(tab: ConfigTab, isolated_ini_loader, monkeypatch) -> None:
    errors: list[str] = []
    monkeypatch.setattr(QMessageBox, "critical", lambda _parent, _title, text: errors.append(text))
    model = isolated_ini_loader.advanced_options
    control = tab.rows["advanced_options", "fast_vision_mode_coordinates"].control
    assert isinstance(control, QLineEdit)
    control.setText("1 2 3")

    assert not tab.save(model, "advanced_options", "fast_vision_mode_coordinates", "1 2 3")

    assert control.text() == "None"
    assert model.fast_vision_mode_coordinates is None
    assert len(errors) == 1


def test_saving_max_stash_tabs_refreshes_chest_tab_checkboxes(tab: ConfigTab, isolated_ini_loader) -> None:
    chest_tabs = tab.rows["general", "check_chest_tabs"].control
    assert isinstance(chest_tabs, QChestTabWidget)
    assert len(chest_tabs.all_checkboxes) == 7

    assert tab.save(isolated_ini_loader.general, "general", "max_stash_tabs", "6")

    assert len(chest_tabs.all_checkboxes) == 6


def test_changing_theme_setting_notifies_callback(qapp, isolated_ini_loader) -> None:
    calls: list[None] = []
    config_tab = ConfigTab(theme_changed_callback=lambda: calls.append(None))

    config_tab.save(isolated_ini_loader.general, "general", "colorblind_mode", "False")
    assert calls == []
    config_tab.save(isolated_ini_loader.general, "general", "colorblind_mode", "True")
    assert calls == [None]
    config_tab.close()


def test_search_hides_non_matching_rows_and_restores_them(tab: ConfigTab) -> None:
    tab.search_input.setText("colorblind")

    assert not tab.rows["general", "colorblind_mode"].label.isHidden()
    assert tab.rows["general", "mark_as_favorite"].label.isHidden()
    assert tab.nav_list.isHidden()

    tab.search_input.setText("")

    assert all(not row.label.isHidden() for row in tab.rows.values())
    assert not tab.nav_list.isHidden()


def test_reset_category_restores_defaults_of_that_category_only(tab: ConfigTab, isolated_ini_loader) -> None:
    hotkey_row = next(row for row in tab.rows.values() if row.group is tab._group_boxes[SettingsCategory.HOTKEYS])
    other_row = tab.rows["general", "mark_as_favorite"]
    model = tab._settings_store.model_for_section(hotkey_row.section)
    default = getattr(model, hotkey_row.key)
    tab.save(model, hotkey_row.section, hotkey_row.key, "f3")
    tab.save(isolated_ini_loader.general, "general", "mark_as_favorite", "False")

    tab._reset_current_category(SettingsCategory.HOTKEYS)

    assert getattr(model, hotkey_row.key) == default
    assert isolated_ini_loader.general.mark_as_favorite is False
    assert other_row.group is not hotkey_row.group
