from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QCompleter, QDialog, QFormLayout, QLabel, QVBoxLayout, QWidget

from src.desktop.widgets import IgnoreScrollWheelComboBox
from src.game_data import GameCatalog
from src.profiles.editor.dialogs import ok_cancel_buttons


class AddAspectUpgrade(QDialog):
    def __init__(self, aspect_upgrades: list[str], parent: QWidget | None = None) -> None:
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
        self.name_input.addItems([name for name in GameCatalog().aspect_list if name not in aspect_upgrades])
        self.form_layout.addRow(self.name_label, self.name_input)
        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addWidget(ok_cancel_buttons(self))
        self.setLayout(self.main_layout)

    def get_value(self) -> str:
        return self.name_input.currentText()
