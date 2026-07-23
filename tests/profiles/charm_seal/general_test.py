import importlib


def test_general_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.charm_seal.general")
    assert module.CHARMS_TABNAME == "Charms"
