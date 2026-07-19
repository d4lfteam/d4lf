"""Small Qt widgets shared by capability-owned desktop interfaces."""

from typing import override

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QCheckBox, QStyle, QStyleOptionButton

_DEFAULT_ACCENT = "#23fc5d"
_accent_color = _DEFAULT_ACCENT


def set_accent_color(color: str) -> None:
    """Set the accent used by subsequently painted shared checkboxes."""
    global _accent_color
    _accent_color = color


class CheckmarkCheckBox(QCheckBox):
    """A checkbox that draws the configured accent-colored checkmark."""

    @override
    def paintEvent(self, a0: QPaintEvent | None) -> None:
        super().paintEvent(a0)

        if not self.isChecked():
            return

        style = self.style()
        if style is None:
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            option = QStyleOptionButton()
            self.initStyleOption(option)
            indicator_rect = style.subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, self)

            pen = QPen(QColor(_accent_color))
            pen.setWidth(2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            x0, y0, width, height = (
                indicator_rect.x(),
                indicator_rect.y(),
                indicator_rect.width(),
                indicator_rect.height(),
            )
            painter.drawLine(
                int(x0 + width * 0.2), int(y0 + height * 0.5), int(x0 + width * 0.45), int(y0 + height * 0.75)
            )
            painter.drawLine(
                int(x0 + width * 0.45), int(y0 + height * 0.75), int(x0 + width * 0.8), int(y0 + height * 0.25)
            )
        finally:
            painter.end()
