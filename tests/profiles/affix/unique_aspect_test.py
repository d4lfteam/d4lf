import importlib


def test_unique_aspect_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.affix.unique_aspect")
    assert hasattr(module, "UniqueAspectWidget")
