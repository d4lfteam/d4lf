import importlib


def test_dialogs_delete_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.editor.dialogs.delete")
    assert hasattr(module, "DeleteItem")
