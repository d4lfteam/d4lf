from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QApplication, QWidget

from src.app.dashboard.drag import DragHandleButton

if TYPE_CHECKING:
    from PyQt6.QtGui import QMouseEvent


def test_drag_handle_forwards_mouse_events() -> None:
    _app = QApplication.instance() or QApplication([])
    row_widget = QWidget()
    received: list[tuple[QMouseEvent | None, QWidget, QWidget]] = []

    def start_drag(event: QMouseEvent | None, row: QWidget, handle: QWidget) -> None:
        received.append((event, row, handle))

    drag_handle = DragHandleButton(row_widget, start_drag)
    drag_handle.mouseMoveEvent(None)

    assert received == [(None, row_widget, drag_handle)]
