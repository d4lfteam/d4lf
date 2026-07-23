from src.app.dashboard import ActivityLogWidget, DragHandleButton


def test_dashboard_interface_exposes_widgets() -> None:
    assert ActivityLogWidget is not None
    assert DragHandleButton is not None
