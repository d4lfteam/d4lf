from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.game_data import GameCatalog, ItemType, is_weapon

AFFIXES_TABNAME = "Affixes"
AFFIX_VALUE_MODE = "Value"
AFFIX_PERCENT_MODE = "Min %"
UNIQUE_ASPECTS_TITLE = "Unique Aspects"


class ItemTypePicker(QDialog):
    def __init__(self, parent: QWidget | None, item_types: list[ItemType], selected_item_types: list[ItemType]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Item Types")
        self.resize(650, 500)
        self.checkboxes: dict[ItemType, QCheckBox] = {}

        selected_item_type_set = set(selected_item_types)
        weapon_item_types = [
            item_type for item_type in item_types if is_weapon(item_type) or item_type == ItemType.Shield
        ]
        weapon_item_type_set = set(weapon_item_types)
        non_weapon_item_types = [item_type for item_type in item_types if item_type not in weapon_item_type_set]

        layout = QVBoxLayout(self)
        picker_layout = QHBoxLayout()
        picker_layout.addWidget(self._create_item_type_group("Weapons", weapon_item_types, selected_item_type_set))
        picker_layout.addWidget(
            self._create_item_type_group("Non-weapons", non_weapon_item_types, selected_item_type_set)
        )
        layout.addLayout(picker_layout)

        note_label = QLabel("If no item types are selected, all item types will be evaluated for this filter.")
        note_label.setWordWrap(True)
        layout.addWidget(note_label)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        clear_button = button_box.addButton("Clear", QDialogButtonBox.ButtonRole.ResetRole)
        if clear_button is not None:
            clear_button.clicked.connect(self.clear_selection)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _create_item_type_group(
        self, title: str, item_types: list[ItemType], selected_item_types: set[ItemType]
    ) -> QGroupBox:
        group_box = QGroupBox(title)
        group_layout = QVBoxLayout(group_box)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for item_type in item_types:
            checkbox = QCheckBox(GameCatalog().item_type_label(item_type))
            checkbox.setChecked(item_type in selected_item_types)
            self.checkboxes[item_type] = checkbox
            content_layout.addWidget(checkbox)

        scroll_area.setWidget(content_widget)
        group_layout.addWidget(scroll_area)
        return group_box

    def clear_selection(self) -> None:
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def get_selected_item_types(self) -> list[ItemType]:
        return [item_type for item_type, checkbox in self.checkboxes.items() if checkbox.isChecked()]
