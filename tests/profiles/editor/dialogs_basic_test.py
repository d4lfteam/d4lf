import importlib


def test_dialogs_basic_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.dialogs_basic")
    assert hasattr(module, "MinPowerDialog")
