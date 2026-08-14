from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class DeleteItem(QDialog):
    def __init__(self, item_names: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Delete Items")
        self.setFixedSize(300, 200)
        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.groupbox = QGroupBox("Items")
        scroll_area = QScrollArea(self)
        scroll_widget = QWidget(scroll_area)
        scrollable_layout = QVBoxLayout(scroll_widget)
        self.groupbox_layout = QVBoxLayout()
        self.groupbox_layout.addWidget(QLabel("Select items to delete:"))
        self.checkbox_list: list[QCheckBox] = []
        for name in item_names:
            checkbox = QCheckBox(name)
            scrollable_layout.addWidget(checkbox)
            self.checkbox_list.append(checkbox)
        scroll_widget.setLayout(scrollable_layout)
        scroll_area.setWidget(scroll_widget)
        self.groupbox_layout.addWidget(scroll_area)
        self.groupbox.setLayout(self.groupbox_layout)
        buttons = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)
        buttons.addWidget(self.okButton)
        buttons.addWidget(self.cancelButton)
        self.main_layout.addWidget(self.groupbox)
        self.main_layout.addLayout(buttons)
        self.setLayout(self.main_layout)

    def get_value(self) -> list[str]:
        return [checkbox.text() for checkbox in self.checkbox_list if checkbox.isChecked()]
