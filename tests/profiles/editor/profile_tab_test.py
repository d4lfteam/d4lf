import importlib


def test_profile_tab_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.profile_tab")
    assert hasattr(module, "ProfileTab")
