"""Profile-dashboard drag-and-drop behavior."""

from typing import TYPE_CHECKING, override

from PyQt6.QtCore import QMimeData, Qt
from PyQt6.QtGui import QDrag, QDragEnterEvent, QDragMoveEvent, QDropEvent, QMouseEvent
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QPushButton, QWidget

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.app.dashboard.core import ActivityLogWidget


class DragHandleButton(QPushButton):
    def __init__(
        self,
        row_widget: QWidget,
        start_drag: Callable[[QMouseEvent | None, QWidget, QWidget], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("⠿", parent)
        self._row_widget = row_widget
        self._start_drag = start_drag

    @override
    def mouseMoveEvent(self, a0: QMouseEvent | None) -> None:
        self._start_drag(a0, self._row_widget, self)


class ActivityProfileDragMixin:
    def _start_drag(self: ActivityLogWidget, event: QMouseEvent | None, row_widget: QWidget, handle: QWidget) -> None:
        if event is None:
            return
        if event.buttons() != Qt.MouseButton.LeftButton:
            return
        click_pos = handle.mapTo(row_widget, event.position().toPoint())
        drag = QDrag(row_widget)
        mime = QMimeData()
        mime.setText(str(id(row_widget)))
        drag.setMimeData(mime)
        pixmap = row_widget.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(click_pos)
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.3)
        row_widget.setGraphicsEffect(opacity_effect)
        idx = self.profile_layout.indexOf(row_widget)
        self.profile_layout.insertWidget(idx, self.drop_indicator)
        self.drop_indicator.show()
        drag.exec(Qt.DropAction.MoveAction)
        row_widget.setGraphicsEffect(None)
        self.drop_indicator.hide()

    def dragEnterEvent(self: ActivityLogWidget, a0: QDragEnterEvent | None) -> None:  # ruff:ignore[invalid-function-name]
        if a0 is None:
            return
        mime_data = a0.mimeData()
        if mime_data is not None and mime_data.hasText():
            a0.acceptProposedAction()

    def dragMoveEvent(self: ActivityLogWidget, a0: QDragMoveEvent | None) -> None:  # ruff:ignore[invalid-function-name]
        if a0 is None:
            return
        mime_data = a0.mimeData()
        if mime_data is None:
            return
        source_id = mime_data.text()

        # Auto-scroll the list if dragging near the top or bottom edges.
        global_pos = self.mapToGlobal(a0.position().toPoint())
        viewport = self.profile_scroll.viewport()
        if viewport is None:
            return
        viewport_pos = viewport.mapFromGlobal(global_pos)
        margin = 40
        if viewport_pos.y() < margin:
            sb = self.profile_scroll.verticalScrollBar()
            if sb is not None:
                sb.setValue(sb.value() - 10)
        elif viewport_pos.y() > viewport.height() - margin:
            sb = self.profile_scroll.verticalScrollBar()
            if sb is not None:
                sb.setValue(sb.value() + 10)

        pos = self.profile_container.mapFrom(self, a0.position().toPoint())
        dragged_row = None
        current_idx = -1
        for i in range(self.profile_layout.count()):
            item = self.profile_layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget and str(id(widget)) == source_id:
                dragged_row = widget
                current_idx = i
                break
        if not dragged_row:
            return
        for i in range(self.profile_layout.count()):
            item = self.profile_layout.itemAt(i)
            if item is None:
                continue
            target_row = item.widget()
            if not target_row or target_row in (dragged_row, self.drop_indicator):
                continue
            rect = target_row.geometry()
            mid_y = rect.center().y()
            if (i > current_idx and pos.y() > mid_y) or (i < current_idx and pos.y() < mid_y):
                self.profile_layout.insertWidget(i, self.drop_indicator)
                self.profile_layout.insertWidget(i, dragged_row)
                break
        a0.acceptProposedAction()

    def dropEvent(self: ActivityLogWidget, a0: QDropEvent | None) -> None:  # ruff:ignore[invalid-function-name]
        self._on_toggle()
        self._update_zebra_striping()
        if a0 is not None:
            a0.acceptProposedAction()

    def _update_zebra_striping(self: ActivityLogWidget) -> None:
        """Update alternating background colors for currently visible rows."""
        visible_count = 0
        for i in range(self.profile_layout.count()):
            item = self.profile_layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget and widget.objectName() == "profile-row" and not widget.isHidden():
                widget.setProperty("alt", visible_count % 2 == 0)
                style = widget.style()
                if style is not None:
                    style.polish(widget)
                visible_count += 1

    def _filter_profiles(self: ActivityLogWidget, text: str) -> None:
        query = text.lower()
        for name, row in self._rows.items():
            row.setVisible(query in name.lower())
        self._update_zebra_striping()
