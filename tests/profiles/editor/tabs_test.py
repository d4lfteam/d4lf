import importlib


def test_tabs_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.tabs")
    assert hasattr(module, "TabGroupWidget")
