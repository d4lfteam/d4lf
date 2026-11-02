from src.profiles.editor.dialogs import MinPowerDialog


def test_dialogs_interface_exposes_shared_dialogs() -> None:
    assert MinPowerDialog is not None
