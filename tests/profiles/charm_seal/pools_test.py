import importlib


def test_pools_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.charm_seal.pools")
    assert module.CHARMS_TABNAME == "Charms"
