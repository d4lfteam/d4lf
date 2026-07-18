import importlib


def test_profile_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.profile")
    assert hasattr(module, "ProfileEditor")
