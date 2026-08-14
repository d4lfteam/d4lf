from typing import override

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.game_data import GameCatalog, ItemRarity
from src.profiles import TributeFilterModel
from src.profiles.editor.dialogs import IgnoreScrollWheelComboBox


class CreateTribute(QDialog):
    def __init__(self, tributes: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.tributes = tributes

        self.setWindowTitle("Create Tribute")
        self.setFixedSize(300, 150)

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.name_label = QLabel("Tribute:")
        self.name_input = IgnoreScrollWheelComboBox()
        self.name_input.setEditable(True)
        self.name_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        name_completer = self.name_input.completer()
        if name_completer is not None:
            name_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.name_input.addItems(sorted(GameCatalog().tribute_dict.values()))
        self.form_layout.addRow(self.name_label, self.name_input)
        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)

        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addLayout(self.buttonLayout)

        self.setLayout(self.main_layout)

    @override
    def accept(self) -> None:
        reverse_dict = {v: k for k, v in GameCatalog().tribute_dict.items()}
        tribute_name = reverse_dict.get(self.name_input.currentText())
        if tribute_name is None:
            QMessageBox.warning(self, "Warning", "Select a valid tribute from the list.")
            return
        if tribute_name in self.tributes:
            QMessageBox.warning(self, "Warning", "Tribute already exist. You can modify the existing one.")
            return
        super().accept()

    def get_value(self) -> TributeFilterModel:
        reverse_dict = {v: k for k, v in GameCatalog().tribute_dict.items()}
        tribute_name = reverse_dict.get(self.name_input.currentText())
        if tribute_name is None:
            msg = "Select a valid tribute from the list."
            raise ValueError(msg)
        return TributeFilterModel(name=[tribute_name], rarities=[])


class AddTributeRarity(QDialog):
    def __init__(self, rarities: list[ItemRarity], parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.rarities = {ItemRarity(rarity) for rarity in rarities}

        self.setWindowTitle("Add Tribute Rarity")
        self.setFixedSize(300, 150)

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.rarity_label = QLabel("Rarity:")
        self.rarity_input = IgnoreScrollWheelComboBox()
        self.rarity_input.setEditable(True)
        self.rarity_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        rarity_completer = self.rarity_input.completer()
        if rarity_completer is not None:
            rarity_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.rarity_input.addItems([rarity.name for rarity in ItemRarity])
        self.form_layout.addRow(self.rarity_label, self.rarity_input)
        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)

        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addLayout(self.buttonLayout)

        self.setLayout(self.main_layout)

    @override
    def accept(self) -> None:
        rarity_name = self.rarity_input.currentText()
        if rarity_name not in ItemRarity.__members__:
            QMessageBox.warning(self, "Warning", "Select a valid rarity from the list.")
            return

        rarity = ItemRarity[rarity_name]
        if rarity in self.rarities:
            QMessageBox.warning(self, "Warning", "Rarity already exists in this tribute filter.")
            return

        super().accept()

    def get_value(self) -> TributeFilterModel:
        rarity = ItemRarity[self.rarity_input.currentText()]
        return TributeFilterModel(name=[], rarities=[rarity])


class RemoveTribute(QDialog):
    def __init__(self, tributes: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tributes = tributes
        self.setWindowTitle("Delete Tributes")
        self.groupbox = QGroupBox("Tributes")
        self.setFixedSize(300, 300)

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area = QScrollArea(self)
        scroll_widget = QWidget(scroll_area)
        scrollable_layout = QVBoxLayout(scroll_widget)
        self.groupbox_layout = QVBoxLayout()

        label = QLabel("Select Tributes to delete:")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.groupbox_layout.addWidget(label)

        self.checkbox_list: list[QCheckBox] = []
        for tribute in self.tributes:
            checkbox = QCheckBox(str(GameCatalog().tribute_dict[tribute])) if tribute else QCheckBox("None")
            scrollable_layout.addWidget(checkbox)
            self.checkbox_list.append(checkbox)
        scroll_widget.setLayout(scrollable_layout)
        scroll_area.setWidget(scroll_widget)
        self.groupbox_layout.addWidget(scroll_area)
        self.groupbox.setLayout(self.groupbox_layout)
        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)

        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.main_layout.addWidget(self.groupbox)
        self.main_layout.addLayout(self.buttonLayout)

        self.setLayout(self.main_layout)

    def get_value(self) -> list[str | None]:
        reverse_dict = {v: k for k, v in GameCatalog().tribute_dict.items()}
        return [reverse_dict.get(checkbox.text()) for checkbox in self.checkbox_list if checkbox.isChecked()]
