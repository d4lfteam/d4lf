import importlib


def test_pickers_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.pickers")
    assert hasattr(module, "RarityPicker")
