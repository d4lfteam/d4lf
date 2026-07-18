import importlib


def test_container_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.container")
    assert hasattr(module, "Container")
