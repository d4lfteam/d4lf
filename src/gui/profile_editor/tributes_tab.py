from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.config.profile_models import ItemRarity, TributeFilterModel
from src.dataloader import Dataloader
from src.gui.models.dialog import AddTributeRarity, CreateTribute

TRIBUTES_TABNAME = "Tributes"
_TRIBUTE_PREFIX = "Tribute: "
_RARITY_PREFIX = "Rarities: "


class TributesTab(QWidget):
    def __init__(self, tributes: TributeFilterModel | None, parent=None):
        super().__init__(parent)
        self.tributes = tributes if tributes is not None else TributeFilterModel()
        self.list_widget = QListWidget()
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
            "Add tribute names and tribute rarities you want to keep. Name and rarity constraints are ANDed together."
        )
        label.setWordWrap(True)
        main_layout.addWidget(label)

        button_layout = QHBoxLayout()
        add_tribute_button = QPushButton("Add Tribute")
        add_tribute_button.clicked.connect(self._add_tribute)
        button_layout.addWidget(add_tribute_button)

        add_rarity_button = QPushButton("Add Rarity")
        add_rarity_button.clicked.connect(self._add_rarity)
        button_layout.addWidget(add_rarity_button)

        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_selected)
        button_layout.addWidget(remove_button)
        main_layout.addLayout(button_layout)

        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._reload_list_widget()
        main_layout.addWidget(self.list_widget)
        self.setLayout(main_layout)

    def _reload_list_widget(self):
        self.list_widget.clear()
        for tribute_name in self.tributes.name:
            display_name = Dataloader().tribute_dict.get(tribute_name, tribute_name)
            self.list_widget.addItem(f"{_TRIBUTE_PREFIX}{display_name}")
        for rarity in self.tributes.rarities:
            self.list_widget.addItem(f"{_RARITY_PREFIX}{ItemRarity(rarity).name}")

    def _add_tribute(self):
        dialog = CreateTribute(self.tributes.name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            value = dialog.get_value()
            for tribute_name in value.name:
                if tribute_name not in self.tributes.name:
                    self.tributes.name.append(tribute_name)
            self._reload_list_widget()

    def _add_rarity(self):
        dialog = AddTributeRarity(self.tributes.rarities)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            value = dialog.get_value()
            for rarity in value.rarities:
                if rarity not in self.tributes.rarities:
                    self.tributes.rarities.append(rarity)
            self._reload_list_widget()

    def remove_selected(self):
        rows = sorted({self.list_widget.row(item) for item in self.list_widget.selectedItems()}, reverse=True)
        if not rows:
            QMessageBox.warning(self, "Warning", "Select at least one tribute rule to remove.")
            return

        for row in rows:
            text = self.list_widget.item(row).text()
            if text.startswith(_TRIBUTE_PREFIX):
                selected_name = text.removeprefix(_TRIBUTE_PREFIX)
                reverse_dict = {value: key for key, value in Dataloader().tribute_dict.items()}
                normalized_name = reverse_dict.get(selected_name, selected_name)
                if normalized_name in self.tributes.name:
                    self.tributes.name.remove(normalized_name)
            elif text.startswith(_RARITY_PREFIX):
                selected_rarity = text.removeprefix(_RARITY_PREFIX)
                if selected_rarity in ItemRarity.__members__:
                    rarity = ItemRarity[selected_rarity]
                    if rarity in self.tributes.rarities:
                        self.tributes.rarities.remove(rarity)

        self._reload_list_widget()
