import importlib


def test_widgets_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.sigil.widgets")
    assert hasattr(module, "ConditionWidget")
