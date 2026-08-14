import importlib

from pydantic import BaseModel, Field

from src.settings.loader import PARAMS_INI, IniConfigLoaderType
from src.settings.store import SettingsStore


def test_set_value_validates_and_persists(isolated_ini_loader: IniConfigLoaderType) -> None:
    store = SettingsStore(loader=isolated_ini_loader)
    model = isolated_ini_loader.general

    result = store.set_value(model, "general", "max_stash_tabs", 6)

    assert result.success is True
    assert result.previous_value == 7
    assert result.validation_error is None
    assert isolated_ini_loader.general.max_stash_tabs == 6
    assert "max_stash_tabs = 6" in (isolated_ini_loader.user_dir / PARAMS_INI).read_text(encoding="utf-8")


def test_set_value_reports_validation_failure_and_preserves_previous_value(
    isolated_ini_loader: IniConfigLoaderType,
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


def test_default_value_for_supports_default_and_default_factory(isolated_ini_loader: IniConfigLoaderType) -> None:
    store = SettingsStore(loader=isolated_ini_loader)

    assert store.default_value_for(isolated_ini_loader.general, "max_stash_tabs") == 7
    assert store.default_value_for(_DefaultFactoryModel(), "values") == [1, 2, 3]


def test_reset_category_resets_only_requested_settings(isolated_ini_loader: IniConfigLoaderType) -> None:
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


def test_reset_field_restores_single_setting_default(isolated_ini_loader: IniConfigLoaderType) -> None:
    store = SettingsStore(loader=isolated_ini_loader)
    general = isolated_ini_loader.general
    store.set_value(general, "general", "max_stash_tabs", 6)

    change = store.reset_field(general, "general", "max_stash_tabs")

    assert change == ("general", "max_stash_tabs", 7)
    assert isolated_ini_loader.general.max_stash_tabs == 7


def test_reset_all_restores_defaults(isolated_ini_loader: IniConfigLoaderType) -> None:
    store = SettingsStore(loader=isolated_ini_loader)
    general = isolated_ini_loader.general
    store.set_value(general, "general", "run_vision_mode_on_startup", False)

    store.reset_all()

    assert isolated_ini_loader.general.run_vision_mode_on_startup is True


def test_config_tab_constructs_without_error(qapp, isolated_ini_loader: IniConfigLoaderType) -> None:
    settings_tab_module = importlib.import_module("src.settings.tab")
    config_tab_class = settings_tab_module.ConfigTab

    tab = config_tab_class()
    tab.close()
