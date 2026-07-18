import logging
from typing import TYPE_CHECKING

from src.settings.loader import PARAMS_INI, IniConfigLoader

if TYPE_CHECKING:
    import pytest


class TestIniConfigLoader:
    def test_reload_if_changed_updates_models_and_revision(self, isolated_ini_loader: IniConfigLoader) -> None:
        loader = isolated_ini_loader
        revision_before_change = loader.config_revision
        config_path = loader.user_dir / PARAMS_INI
        config_path.write_text("[general]\nrun_vision_mode_on_startup = false\n", encoding="utf-8")

        assert loader.reload_if_changed() is True
        assert loader.general.run_vision_mode_on_startup is False
        assert loader.config_revision > revision_before_change
        assert loader.reload_if_changed() is False

    def test_property_access_auto_reloads_changed_config(self, isolated_ini_loader: IniConfigLoader) -> None:
        loader = isolated_ini_loader
        config_path = loader.user_dir / PARAMS_INI
        config_path.write_text("[general]\nrun_vision_mode_on_startup = false\n", encoding="utf-8")

        assert loader.general.run_vision_mode_on_startup is False

    def test_save_value_updates_model_without_reloading_from_file(self, isolated_ini_loader: IniConfigLoader) -> None:
        loader = isolated_ini_loader

        loader.save_value("general", "profiles", "alpha, beta")

        assert loader.general.profiles == ["alpha", "beta"]

    def test_save_value_notifies_change_listeners(self, isolated_ini_loader: IniConfigLoader) -> None:
        loader = isolated_ini_loader
        notified_changes: list[frozenset[str]] = []

        loader.register_change_listener(notified_changes.append)
        loader.save_value("advanced_options", "log_lvl", "debug")

        assert notified_changes == [frozenset({"advanced_options.log_lvl"})]

    def test_reload_if_changed_notifies_changed_keys(self, isolated_ini_loader: IniConfigLoader) -> None:
        loader = isolated_ini_loader
        notified_changes: list[frozenset[str]] = []
        config_path = loader.user_dir / PARAMS_INI
        loader.register_change_listener(notified_changes.append)

        config_path.write_text("[general]\nvision_mode_type = fast\n", encoding="utf-8")
        loader.reload_if_changed()

        assert notified_changes == [frozenset({"general.vision_mode_type"})]

    def test_reload_if_changed_removes_defunct_model_keys(
        self, isolated_ini_loader: IniConfigLoader, caplog: pytest.LogCaptureFixture
    ) -> None:
        loader = isolated_ini_loader
        config_path = loader.user_dir / PARAMS_INI
        config_path.write_text(
            "[general]\nrun_vision_mode_on_startup = false\nremoved_setting = true\n\n"
            "[paragon_overlay]\ncell_size = 12\n",
            encoding="utf-8",
        )

        with caplog.at_level(logging.WARNING, logger="src.settings.loader"):
            assert loader.reload_if_changed() is True

        config_text = config_path.read_text(encoding="utf-8")
        assert loader.general.run_vision_mode_on_startup is False
        assert "removed_setting" not in config_text
        assert "[paragon_overlay]" in config_text
        assert "cell_size = 12" in config_text
        assert "Deprecated key=removed_setting" in caplog.text
        cleanup_records = loader.consume_deferred_cleanup_log_records()
        assert [record.getMessage() for record in cleanup_records] == [
            "Deprecated key=removed_setting found in [general]. Removing it from params.ini."
        ]
        assert loader.consume_deferred_cleanup_log_records() == []
