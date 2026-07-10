import importlib
import os
import sys
import types
from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel, Field
from PyQt6.QtWidgets import QApplication, QCheckBox

from src.config.loader import PARAMS_INI, IniConfigLoader
from src.gui.settings_store import SettingsStore

if TYPE_CHECKING:
    from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def isolated_ini_loader(tmp_path: Path):
    loader = IniConfigLoader()
    original_user_dir = loader._user_dir
    original_parser = loader._parser
    original_general = loader._general
    original_char = loader._char
    original_advanced_options = loader._advanced_options
    original_signature = loader._last_config_signature
    original_revision = loader._config_revision
    original_listeners = list(loader._change_listeners)
    original_deferred_cleanup_logs = list(loader._deferred_cleanup_log_records)
    original_defer_cleanup_logs = loader._defer_cleanup_log_records

    loader._user_dir = tmp_path
    loader._change_listeners = []
    loader._deferred_cleanup_log_records = []
    loader._defer_cleanup_log_records = True
    loader.load(clear=True)

    try:
        yield loader
    finally:
        loader._user_dir = original_user_dir
        loader._parser = original_parser
        loader._general = original_general
        loader._char = original_char
        loader._advanced_options = original_advanced_options
        loader._last_config_signature = original_signature
        loader._config_revision = original_revision
        loader._change_listeners = original_listeners
        loader._deferred_cleanup_log_records = original_deferred_cleanup_logs
        loader._defer_cleanup_log_records = original_defer_cleanup_logs


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_set_value_validates_and_persists(isolated_ini_loader: IniConfigLoader) -> None:
    store = SettingsStore(loader=isolated_ini_loader)
    model = isolated_ini_loader.general

    result = store.set_value(model, "general", "max_stash_tabs", 6)

    assert result.success is True
    assert result.previous_value == 7
    assert result.validation_error is None
    assert isolated_ini_loader.general.max_stash_tabs == 6
    assert "max_stash_tabs = 6" in (isolated_ini_loader.user_dir / PARAMS_INI).read_text(encoding="utf-8")


def test_set_value_reports_validation_failure_and_preserves_previous_value(
    isolated_ini_loader: IniConfigLoader,
) -> None:
    store = SettingsStore(loader=isolated_ini_loader)
    model = isolated_ini_loader.general

    result = store.set_value(model, "general", "max_stash_tabs", 8)

    assert result.success is False
    assert result.previous_value == 7
    assert result.validation_error is not None
    assert "must be 6 or 7" in result.validation_error
    assert isolated_ini_loader.general.max_stash_tabs == 7


class _DefaultFactoryModel(BaseModel):
    values: list[int] = Field(default_factory=lambda: [1, 2, 3])


def test_default_value_for_supports_default_and_default_factory(isolated_ini_loader: IniConfigLoader) -> None:
    store = SettingsStore(loader=isolated_ini_loader)

    assert store.default_value_for(isolated_ini_loader.general, "max_stash_tabs") == 7
    assert store.default_value_for(_DefaultFactoryModel(), "values") == [1, 2, 3]


def test_reset_category_resets_only_requested_settings(isolated_ini_loader: IniConfigLoader) -> None:
    store = SettingsStore(loader=isolated_ini_loader)
    general = isolated_ini_loader.general

    store.set_value(general, "general", "max_stash_tabs", 6)
    store.set_value(general, "general", "check_chest_tabs", "1")
    store.set_value(general, "general", "run_vision_mode_on_startup", False)

    changes = store.reset_category([(general, "general", "max_stash_tabs"), (general, "general", "check_chest_tabs")])

    assert ("general", "max_stash_tabs", 7) in changes
    assert ("general", "check_chest_tabs", [0, 1]) in changes
    assert isolated_ini_loader.general.max_stash_tabs == 7
    assert isolated_ini_loader.general.check_chest_tabs == [0, 1]
    assert isolated_ini_loader.general.run_vision_mode_on_startup is False


def test_reset_field_restores_single_setting_default(isolated_ini_loader: IniConfigLoader) -> None:
    store = SettingsStore(loader=isolated_ini_loader)
    general = isolated_ini_loader.general
    store.set_value(general, "general", "max_stash_tabs", 6)

    change = store.reset_field(general, "general", "max_stash_tabs")

    assert change == ("general", "max_stash_tabs", 7)
    assert isolated_ini_loader.general.max_stash_tabs == 7


def test_reset_all_restores_defaults(isolated_ini_loader: IniConfigLoader) -> None:
    store = SettingsStore(loader=isolated_ini_loader)
    general = isolated_ini_loader.general
    store.set_value(general, "general", "run_vision_mode_on_startup", False)

    store.reset_all()

    assert isolated_ini_loader.general.run_vision_mode_on_startup is True


def test_config_tab_constructs_without_error(qapp, isolated_ini_loader: IniConfigLoader) -> None:
    checkmark_checkbox_module = types.ModuleType("src.gui.models.checkmark_checkbox")
    checkmark_checkbox_module.CheckmarkCheckBox = QCheckBox
    sys.modules["src.gui.models.checkmark_checkbox"] = checkmark_checkbox_module

    settings_tab_module = importlib.import_module("src.gui.settings_tab")
    config_tab_class = settings_tab_module.ConfigTab

    tab = config_tab_class()
    tab.close()
