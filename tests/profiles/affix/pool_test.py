import importlib


def test_pool_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.affix.pool")
    assert hasattr(module, "AffixPoolWidget")
