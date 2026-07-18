import importlib


def test_session_store_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.session_store")
    assert hasattr(module, "QSettingsLastOpenedStore")
