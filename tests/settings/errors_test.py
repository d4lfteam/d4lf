from pathlib import Path

from src.settings.errors import SettingsLoadError


def test_settings_load_error_preserves_paths_and_original_exception() -> None:
    config_path = Path("params.ini")
    original = ValueError("invalid value")

    error = SettingsLoadError(config_path, original)

    assert error.config_path == config_path
    assert error.original is original
    assert str(config_path) in str(error)
    assert error.log_path.name == "logs"
