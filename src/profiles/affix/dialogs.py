from typing import override

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.game_data import GameCatalog, ItemType
from src.profiles import AffixFilterCountModel, AffixFilterModel, DynamicItemFilterModel, ItemFilterModel


class CreateItem(QDialog):
    def __init__(self, item_list: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Item")
        self.setFixedSize(300, 150)
        self.item_list = item_list
        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()
        self.name_label = QLabel("Item Name:")
        self.name_input = QLineEdit()
        self.form_layout.addRow(self.name_label, self.name_input)
        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addLayout(self.button_layout)
        self.setLayout(self.main_layout)
        self.buttonLayout = self.button_layout
        self.okButton = self.ok_button
        self.cancelButton = self.cancel_button

    @override
    def accept(self) -> None:
        if not self.name_input.text():
            QMessageBox.warning(self, "Warning", "Item name cannot be empty")
            return
        if self.name_input.text() in self.item_list:
            QMessageBox.warning(self, "Warning", "Item name already exist")
            return
        super().accept()

    def get_value(self) -> DynamicItemFilterModel:
        item = ItemFilterModel()
        item.item_type = [ItemType.Amulet]
        item.affix_pool = [
            AffixFilterCountModel(count=[AffixFilterModel(name=next(iter(GameCatalog().affix_dict), ""))], min_count=2)
        ]
        item.min_power = 100
        return DynamicItemFilterModel(root={self.name_input.text(): item})


class DeleteAffixPool(QDialog):
    def __init__(self, nb_affix_pool: int, inherent: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        title = "Delete Inherent Pool" if inherent else "Delete Affix Pool"
        self.setWindowTitle(title)
        self.setFixedSize(300, 200)
        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.groupbox = QGroupBox("Inherent Pool" if inherent else "Affix Pool")
        scroll_area = QScrollArea(self)
        scroll_widget = QWidget(scroll_area)
        scrollable_layout = QVBoxLayout(scroll_widget)
        self.groupbox_layout = QVBoxLayout()
        self.groupbox_layout.addWidget(QLabel("Select items to delete:"))
        self.checkbox_list: list[QCheckBox] = []
        for i in range(nb_affix_pool):
            checkbox = QCheckBox(f"Count {i}")
            scrollable_layout.addWidget(checkbox)
            self.checkbox_list.append(checkbox)
        scroll_widget.setLayout(scrollable_layout)
        scroll_area.setWidget(scroll_widget)
        self.groupbox_layout.addWidget(scroll_area)
        self.groupbox.setLayout(self.groupbox_layout)
        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.main_layout.addWidget(self.groupbox)
        self.main_layout.addLayout(self.button_layout)
        self.setLayout(self.main_layout)
        self.buttonLayout = self.button_layout
        self.okButton = self.ok_button
        self.cancelButton = self.cancel_button

    def get_value(self) -> list[str]:
        return [checkbox.text() for checkbox in self.checkbox_list if checkbox.isChecked()]
