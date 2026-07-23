from src.importing.gui import ImporterWindow


def test_importing_gui_facade_exports_window() -> None:
    assert ImporterWindow.__name__ == "ImporterWindow"
