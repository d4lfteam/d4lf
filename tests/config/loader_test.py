from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from src.config.loader import PARAMS_INI, IniConfigLoader
from src.config.models import JunkRaresType

if TYPE_CHECKING:
    from pathlib import Path


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

    loader._user_dir = tmp_path
    loader._change_listeners = []
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


class TestIniConfigLoader:
    def test_default_junk_rares_is_three_affixes(self, isolated_ini_loader: IniConfigLoader) -> None:
        loader = isolated_ini_loader

        assert loader.general.junk_rares == JunkRaresType.three_affixes

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

    @pytest.mark.parametrize(
        ("config_value", "expected"), [("True", JunkRaresType.all), ("False", JunkRaresType.three_affixes)]
    )
    def test_reload_if_changed_migrates_junk_rares_values(
        self,
        isolated_ini_loader: IniConfigLoader,
        config_value: str,
        expected: JunkRaresType,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        loader = isolated_ini_loader
        config_path = loader.user_dir / PARAMS_INI
        config_path.write_text(f"[general]\njunk_rares = {config_value}\n", encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="src.config.models"):
            assert loader.reload_if_changed() is True

        assert loader.general.junk_rares == expected
        assert f"Deprecated general.junk_rares value={config_value}" in caplog.text
        assert "Please save your settings to persist the new value." in caplog.text
