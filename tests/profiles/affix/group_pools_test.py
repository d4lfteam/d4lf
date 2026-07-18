import importlib


def test_group_pools_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.affix.group_pools")
    assert module.AFFIXES_TABNAME == "Affixes"
