import importlib


def test_widget_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.affix.widget")
    assert hasattr(module, "AffixWidget")
