from typing import TYPE_CHECKING, override

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.game_data import MAX_POWER

if TYPE_CHECKING:
    from PyQt6.QtGui import QWheelEvent


class IgnoreScrollWheelSpinBox(QSpinBox):
    def __init__(self) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    @override
    def wheelEvent(self, e: QWheelEvent | None) -> None:
        if self.hasFocus():
            super().wheelEvent(e)
        elif e is not None:
            e.ignore()


class IgnoreScrollWheelComboBox(QComboBox):
    def __init__(self) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    @override
    def wheelEvent(self, e: QWheelEvent | None) -> None:
        if self.hasFocus():
            super().wheelEvent(e)
        elif e is not None:
            e.ignore()


class _SpinDialog(QDialog):
    title = ""
    label = ""
    minimum = 0
    maximum = 100
    default = 0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.title)
        self.setFixedSize(250, 150)
        form = QFormLayout()
        self.spinBox = IgnoreScrollWheelSpinBox()
        self.spinBox.setRange(self.minimum, self.maximum)
        self.spinBox.setValue(self.default)
        form.addRow(QLabel(self.label), self.spinBox)
        buttons = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)
        buttons.addWidget(self.okButton)
        buttons.addWidget(self.cancelButton)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)

    def get_value(self) -> int:
        return self.spinBox.value()


class MinPowerDialog(_SpinDialog):
    title = "Set Min Power"
    label = "Min Power:"
    maximum = MAX_POWER
    default = MAX_POWER


class MinGreaterDialog(_SpinDialog):
    title = "Set Min Greater Affix"
    label = "Min Greater Affix:"
    maximum = 4


class MinPercentDialog(_SpinDialog):
    title = "Set Min Percent Of Affix"
    label = "Min Percent Of Affix:"
    default = 70
