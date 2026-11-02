from typing import TYPE_CHECKING, override

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

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


def ok_cancel_buttons(dialog: QDialog) -> QDialogButtonBox:
    """Return an OK/Cancel button box wired to the dialog's accept/reject."""
    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    return button_box


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
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(ok_cancel_buttons(self))

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
