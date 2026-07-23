from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.item import Dataloader
from src.profiles import TributeFilterModel
from src.profiles.editor import RarityPicker, rarity_summary
from src.profiles.tribute.dialogs import CreateTribute

TRIBUTES_TABNAME = "Tributes"
_TRIBUTE_PREFIX = "Tribute: "


class TributesTab(QWidget):
    def __init__(self, tributes: TributeFilterModel | None, parent=None):
        super().__init__(parent)
        self.tributes = tributes if tributes is not None else TributeFilterModel()
        self.list_widget = QListWidget()
        self.rarity_line_edit = QLineEdit()
        self.loaded = False

    def load(self):
        if not self.loaded:
            self.setup_ui()
            self.loaded = True

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 20, 0, 20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        label = QLabel(
            "Add tribute names and select rarities you want to keep. Leaving rarities empty keeps all rarities."
        )
        label.setWordWrap(True)
        main_layout.addWidget(label)

        button_layout = QHBoxLayout()
        add_tribute_button = QPushButton("Add Tribute")
        add_tribute_button.clicked.connect(self._add_tribute)
        button_layout.addWidget(add_tribute_button)

        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_selected)
        button_layout.addWidget(remove_button)
        main_layout.addLayout(button_layout)

        self.rarity_line_edit.setReadOnly(True)
        self.refresh_rarity_summary()
        rarity_layout = QHBoxLayout()
        rarity_layout.addWidget(self.rarity_line_edit)
        edit_rarities_button = QPushButton("...")
        edit_rarities_button.setMaximumWidth(40)
        edit_rarities_button.clicked.connect(self.edit_rarities)
        rarity_layout.addWidget(edit_rarities_button)
        rarity_layout.addStretch()
        rarity_form = QFormLayout()
        rarity_form.addRow("Rarities:", rarity_layout)
        main_layout.addLayout(rarity_form)

        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._reload_list_widget()
        main_layout.addWidget(self.list_widget)
        self.setLayout(main_layout)

    def _reload_list_widget(self):
        self.list_widget.clear()
        for tribute_name in self.tributes.name:
            display_name = Dataloader().tribute_dict.get(tribute_name, tribute_name)
            self.list_widget.addItem(f"{_TRIBUTE_PREFIX}{display_name}")

    def _add_tribute(self):
        dialog = CreateTribute(self.tributes.name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            value = dialog.get_value()
            for tribute_name in value.name:
                if tribute_name not in self.tributes.name:
                    self.tributes.name.append(tribute_name)
            self._reload_list_widget()

    def refresh_rarity_summary(self):
        self.rarity_line_edit.setText(rarity_summary(self.tributes.rarities))

    def edit_rarities(self):
        picker = RarityPicker(self, self.tributes.rarities)
        if picker.exec() == QDialog.DialogCode.Accepted:
            self.tributes.rarities = picker.get_selected_rarities()
            self.refresh_rarity_summary()

    def remove_selected(self):
        rows = sorted({self.list_widget.row(item) for item in self.list_widget.selectedItems()}, reverse=True)
        if not rows:
            QMessageBox.warning(self, "Warning", "Select at least one tribute rule to remove.")
            return

        for row in rows:
            item = self.list_widget.item(row)
            if item is None:
                continue
            text = item.text()
            if text.startswith(_TRIBUTE_PREFIX):
                selected_name = text.removeprefix(_TRIBUTE_PREFIX)
                reverse_dict = {value: key for key, value in Dataloader().tribute_dict.items()}
                normalized_name = reverse_dict.get(selected_name, selected_name)
                if normalized_name in self.tributes.name:
                    self.tributes.name.remove(normalized_name)

        self._reload_list_widget()
