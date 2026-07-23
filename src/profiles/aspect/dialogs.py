from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QCompleter, QDialog, QFormLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from src.item import Dataloader
from src.profiles.editor import IgnoreScrollWheelComboBox


class AddAspectUpgrade(QDialog):
    def __init__(self, aspect_upgrades: list[str], parent=None):
        super().__init__(parent)
        self.aspect_upgrades = aspect_upgrades
        self.setWindowTitle("Add Aspect")
        self.setFixedSize(300, 150)
        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()
        self.name_label = QLabel("Aspect:")
        self.name_input = IgnoreScrollWheelComboBox()
        self.name_input.setEditable(True)
        self.name_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer = self.name_input.completer()
        if completer is not None:
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.name_input.addItems([name for name in Dataloader().aspect_list if name not in aspect_upgrades])
        self.form_layout.addRow(self.name_label, self.name_input)
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addLayout(button_layout)
        self.setLayout(self.main_layout)

    def get_value(self) -> str:
        return self.name_input.currentText()
