from src.settings.constants import BASE_DIR, PARAMS_INI


def test_settings_constants_expose_runtime_paths() -> None:
    assert BASE_DIR.is_absolute()
    assert PARAMS_INI == "params.ini"
