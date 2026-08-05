from typing import override

from PyQt6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout

from src.game_data import GameCatalog
from src.profiles import (
    AffixFilterCountModel,
    AffixFilterModel,
    CharmFilterModel,
    DynamicCharmFilterModel,
    DynamicSealFilterModel,
    SealFilterModel,
)
from src.profiles.editor.pickers import CheckboxListDialog


class CreateCharmOrSeal(QDialog):
    """Dialog for creating a new named charm or seal filter."""

    def __init__(self, item_list: list[str], is_charm: bool = True, parent=None):
        super().__init__(parent)
        self.is_charm = is_charm
        label = "Charm" if is_charm else "Seal"
        self.setWindowTitle(f"Create {label}")
        self.setFixedSize(300, 150)
        self.item_list = item_list
        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()
        self.name_label = QLabel(f"{label} Name:")
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
            QMessageBox.warning(self, "Warning", "Name cannot be empty")
            return
        if self.name_input.text() in self.item_list:
            QMessageBox.warning(self, "Warning", "Name already exists")
            return
        super().accept()

    def get_value(self):
        item_name = self.name_input.text()
        affix_dict = GameCatalog().charm_affix_dict if self.is_charm else GameCatalog().seal_affix_dict
        default_affix = AffixFilterModel(name=next(iter(affix_dict.keys()), ""))
        default_pool = AffixFilterCountModel(count=[default_affix], min_count=1, max_count=3)
        if self.is_charm:
            return DynamicCharmFilterModel(root={item_name: CharmFilterModel(affix_pool=[default_pool])})
        return DynamicSealFilterModel(root={item_name: SealFilterModel(affix_pool=[default_pool])})


class SetPicker(CheckboxListDialog[str]):
    """Multi-select dialog for charm set names."""

    def __init__(self, parent, selected_sets: list[str]):
        super().__init__(
            parent,
            window_title="Select Sets",
            group_title="Sets",
            options=sorted(GameCatalog().set_list),
            selected=selected_sets,
            note_text="Select which sets this charm filter should match.",
        )

    def get_selected_sets(self) -> list[str]:
        return self.get_selected()
