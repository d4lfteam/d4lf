from src.profiles.editor.dialogs import DeleteItem, MinPowerDialog


def test_dialogs_interface_exposes_shared_dialogs() -> None:
    assert DeleteItem is not None
    assert MinPowerDialog is not None
