from src.desktop.widgets import CheckmarkCheckBox, set_accent_color


def test_widgets_facade_exports_public_controls() -> None:
    assert CheckmarkCheckBox is not None
    assert callable(set_accent_color)
