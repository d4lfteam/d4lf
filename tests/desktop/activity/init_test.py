from src.desktop.activity import ANSIConsoleWidget, QtLogHandler


def test_activity_facade_exports_widgets() -> None:
    assert ANSIConsoleWidget is not None
    assert QtLogHandler is not None
