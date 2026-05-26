from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QCheckBox, QStyle, QStyleOptionButton


class CheckmarkCheckBox(QCheckBox):
    """A custom QCheckBox that renders a checkmark inside its indicator.

    The checkmark is rendered when the box is checked, using the theme's accent color.
    """

    def paintEvent(self, event):
        super().paintEvent(event)  # Draw the default checkbox background/border

        if not self.isChecked():
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            option = QStyleOptionButton()
            self.initStyleOption(option)
            indicator_rect = self.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, self)

            # Draw a simple checkmark inside the indicator
            pen = QPen(QColor("#23fc5d"))  # Green color from theme
            pen.setWidth(2)  # Adjust thickness as needed
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            x0, y0, w, h = indicator_rect.x(), indicator_rect.y(), indicator_rect.width(), indicator_rect.height()

            # Checkmark coordinates (relative to indicator_rect) - Cast to int for PyQt6 compatibility
            painter.drawLine(int(x0 + w * 0.2), int(y0 + h * 0.5), int(x0 + w * 0.45), int(y0 + h * 0.75))
            painter.drawLine(int(x0 + w * 0.45), int(y0 + h * 0.75), int(x0 + w * 0.8), int(y0 + h * 0.25))
        finally:
            painter.end()
