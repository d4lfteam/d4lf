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

from src.config.models import ItemRarity, TributeFilterModel
from src.dataloader import Dataloader
from src.gui.dialog import AddTributeRarity, CreateTribute

TRIBUTES_TABNAME = "Tributes"


class TributesTab(QWidget):
    def __init__(self, tributes: list[TributeFilterModel] | None, parent=None):
        super().__init__(parent)
        self.tributes = tributes if tributes is not None else []
        self.tribute_list_widget = QListWidget()
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
            "Add tribute names and tribute rarities you want to keep. These rules are evaluated independently."
        )
        label.setWordWrap(True)
        main_layout.addWidget(label)
        button_layout = self.create_button_layout()
        main_layout.addLayout(button_layout)

        self.tribute_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._reload_tribute_list_widget()
        main_layout.addWidget(self.tribute_list_widget)
        self.setLayout(main_layout)

    def create_button_layout(self) -> QHBoxLayout:
        btn_layout = QHBoxLayout()

        add_tribute_btn = QPushButton("Add Tribute")
        add_tribute_btn.clicked.connect(self.add_tribute)

        add_rarity_btn = QPushButton("Add Rarity")
        add_rarity_btn.clicked.connect(self.add_rarity)

        remove_rule_btn = QPushButton("Remove Selected")
        remove_rule_btn.clicked.connect(self.remove_selected)

        btn_layout.addWidget(add_tribute_btn)
        btn_layout.addWidget(add_rarity_btn)
        btn_layout.addWidget(remove_rule_btn)
        return btn_layout

    def _reload_tribute_list_widget(self):
        self.tribute_list_widget.clear()
        for tribute in self.tributes:
            self.tribute_list_widget.addItem(self._display_text(tribute))

    @staticmethod
    def _display_text(tribute: TributeFilterModel) -> str:
        if not tribute.name and not tribute.rarities:
            return "Empty tribute rule"

        parts = []
        if tribute.name:
            tribute_name = Dataloader().tribute_dict.get(tribute.name, tribute.name)
            parts.append(f"Tribute: {tribute_name}")

        if tribute.rarities:
            rarity_names = ", ".join(ItemRarity(rarity).name for rarity in tribute.rarities)
            parts.append(f"Rarities: {rarity_names}")

        return " | ".join(parts)

    def add_tribute(self):
        dialog = CreateTribute(self._existing_tribute_names())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tribute_filter = dialog.get_value()
            self.tributes.append(tribute_filter)
            self.tribute_list_widget.addItem(self._display_text(tribute_filter))

    def add_rarity(self):
        dialog = AddTributeRarity(self._existing_rarities())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tribute_filter = dialog.get_value()
            self.tributes.append(tribute_filter)
            self.tribute_list_widget.addItem(self._display_text(tribute_filter))

    def remove_selected(self):
        rows = sorted(
            {self.tribute_list_widget.row(item) for item in self.tribute_list_widget.selectedItems()}, reverse=True
        )
        if not rows:
            QMessageBox.warning(self, "Warning", "Select at least one tribute rule to remove.")
            return

        for row in rows:
            self.tribute_list_widget.takeItem(row)
            self.tributes.pop(row)

    def _existing_tribute_names(self) -> list[str]:
        return [tribute.name for tribute in self.tributes if tribute.name and not tribute.rarities]

    def _existing_rarities(self) -> list[ItemRarity]:
        return [
            ItemRarity(tribute.rarities[0])
            for tribute in self.tributes
            if tribute.rarities and not tribute.name and len(tribute.rarities) == 1
        ]
