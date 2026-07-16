import subprocess
import sys
from pathlib import Path

import pytest

from src import settings


def test_facade_exposes_typed_defaults_and_hotkey_validation() -> None:
    model = settings.AdvancedOptionsModel()
    assert model.exit_key == "f12"
    assert settings.validate_hotkey("Control+F11") == "ctrl+f11"


def test_hotkey_aliases_have_stable_modifier_order() -> None:
    assert settings.canonicalize_hotkey("F11+Shift+Control") == "ctrl+shift+f11"
    with pytest.raises(ValueError, match="unique"):
        settings.AdvancedOptionsModel(exit_key="f1", run_filter="f1")


def test_resolution_manager_preserves_uhd_reference() -> None:
    manager = settings.get_ui_coordinates()
    assert manager.resolution == (3840, 2160)
    assert manager.offsets.item_descr_line_height == 50
    manager.set_resolution("1920x1080")
    assert manager.resolution == (1920, 1080)
    assert manager.offsets.item_descr_line_height == 25
    manager.set_resolution("3840x2160")


def test_params_path_contract() -> None:
    loader = settings.get_settings()
    assert loader.user_dir == Path.home() / ".d4lf"
    assert settings.PARAMS_INI == "params.ini"


def test_import_is_free_of_platform_and_gui_backends() -> None:
    code = "import sys; import src.settings; assert 'pynput' not in sys.modules; assert 'PyQt6' not in sys.modules"
    result = subprocess.run([sys.executable, "-c", code], check=False, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
