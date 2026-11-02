from typing import override

from PyQt6.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout, QWidget

from src.game_data import GameCatalog, ItemType
from src.profiles import AffixFilterCountModel, AffixFilterModel, DynamicItemFilterModel, ItemFilterModel
from src.profiles.editor.dialogs import ok_cancel_buttons


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
        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addWidget(ok_cancel_buttons(self))
        self.setLayout(self.main_layout)

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
