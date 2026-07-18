import importlib


def test_picker_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.affix.picker")
    assert hasattr(module, "ItemTypePicker")
