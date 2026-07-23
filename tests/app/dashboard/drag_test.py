from PyQt6.QtWidgets import QApplication, QWidget

from src.app.dashboard.drag import DragHandleButton


def test_drag_handle_forwards_mouse_events() -> None:
    _app = QApplication.instance() or QApplication([])
    row_widget = QWidget()
    received: list[tuple[object, QWidget, QWidget]] = []

    def start_drag(event: object, row: QWidget, handle: QWidget) -> None:
        received.append((event, row, handle))

    drag_handle = DragHandleButton(row_widget, start_drag)
    drag_handle.mouseMoveEvent(None)

    assert received == [(None, row_widget, drag_handle)]
