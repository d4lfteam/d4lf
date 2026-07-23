import importlib


def test_dialogs_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.aspect.dialogs")
    assert hasattr(module, "AddAspectUpgrade")
