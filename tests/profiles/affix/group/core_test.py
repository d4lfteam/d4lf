import importlib


def test_group_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.affix.group.core")
    assert hasattr(module, "AffixGroupEditor")
