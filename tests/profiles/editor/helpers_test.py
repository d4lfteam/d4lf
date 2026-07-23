import importlib


def test_helpers_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.helpers")
    assert hasattr(module, "create_readonly_line_edit")
