import importlib
import sys


def test_config_helper_imports_without_keyboard(monkeypatch):
    monkeypatch.setitem(sys.modules, "keyboard", None)
    sys.modules.pop("src.config.helper", None)

    helper = importlib.import_module("src.config.helper")

    assert helper.check_greater_than_zero(1) == 1
    assert helper.validate_hotkey("shift+a") == "shift+a"
