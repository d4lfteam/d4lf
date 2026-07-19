import importlib


def test_profile_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.profile.core")
    assert hasattr(module, "ProfileEditor")
