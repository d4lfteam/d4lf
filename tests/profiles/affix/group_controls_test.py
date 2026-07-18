import importlib


def test_group_controls_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.affix.group_controls")
    assert module.AFFIX_VALUE_MODE == "Value"
