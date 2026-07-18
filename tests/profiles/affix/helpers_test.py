import importlib


def test_helpers_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.affix.helpers")
    assert hasattr(module, "get_affixes_for_set")
