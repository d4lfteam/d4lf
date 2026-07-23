import importlib


def test_dialogs_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.charm_seal.dialogs")
    assert hasattr(module, "CreateCharmOrSeal")
