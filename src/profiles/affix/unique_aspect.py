from typing import TYPE_CHECKING

from PyQt6.QtCore import QSignalBlocker, Qt
from PyQt6.QtGui import QDoubleValidator, QIntValidator
from PyQt6.QtWidgets import QComboBox, QCompleter, QHBoxLayout, QLineEdit, QMessageBox, QWidget

from src.game_data import GameCatalog
from src.profiles.editor.dialogs import IgnoreScrollWheelComboBox

if TYPE_CHECKING:
    from src.profiles import AspectUniqueFilterModel

AFFIXES_TABNAME = "Affixes"
AFFIX_VALUE_MODE = "Value"
AFFIX_PERCENT_MODE = "Min %"
UNIQUE_ASPECTS_TITLE = "Unique Aspects"


class UniqueAspectWidget(QWidget):
    def __init__(self, unique_aspect: AspectUniqueFilterModel, allowed_aspects: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.unique_aspect = unique_aspect
        self.allowed_aspects = allowed_aspects
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.setSpacing(50)

        self.create_aspect_name_combobox()
        self.create_mode_combobox()
        self.create_value_input()
        self.mode_combo.currentTextChanged.connect(self.update_mode)
        self.update_mode(self.mode_combo.currentText())

        layout.addWidget(self.name_combo)
        layout.addWidget(self.mode_combo)
        layout.addWidget(self.value_edit)

        self.setMinimumWidth(850)
        self.setLayout(layout)

    def create_aspect_name_combobox(self):
        self.name_combo = IgnoreScrollWheelComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        name_completer = self.name_combo.completer()
        if name_completer is not None:
            name_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            name_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        aspects = (
            self.allowed_aspects
            if self.allowed_aspects is not None
            else sorted(GameCatalog().aspect_unique_dict.keys())
        )
        self.name_combo.addItems(aspects)
        self.name_combo.setMaximumWidth(600)
        if self.unique_aspect.name in GameCatalog().aspect_unique_dict:
            self.name_combo.setCurrentText(self.unique_aspect.name)
        self.name_combo.currentTextChanged.connect(self.update_name)

    def create_mode_combobox(self):
        self.mode_combo = IgnoreScrollWheelComboBox()
        self.mode_combo.setFixedSize(100, self.mode_combo.sizeHint().height())
        self.mode_combo.addItems([AFFIX_VALUE_MODE, AFFIX_PERCENT_MODE])
        if self.unique_aspect.min_percent_of_aspect:
            self.mode_combo.setCurrentText(AFFIX_PERCENT_MODE)
        else:
            self.mode_combo.setCurrentText(AFFIX_VALUE_MODE)

    def create_value_input(self):
        self.value_edit = QLineEdit()
        self.value_edit.setFixedSize(100, self.value_edit.sizeHint().height())
        self.value_edit.textChanged.connect(self.update_value)

    def update_name(self, current_text=None):
        aspect_name = current_text or self.name_combo.currentText()
        aspect_name = aspect_name.strip()
        if aspect_name not in GameCatalog().aspect_unique_dict:
            return
        self.unique_aspect.name = aspect_name
        self.update_parent_unique_aspects_title()

    def update_parent_unique_aspects_title(self):
        parent = self.parent()
        while parent:
            refresh_title = getattr(parent, "refresh_unique_aspects_title", None)
            if refresh_title is not None:
                refresh_title()
                break
            parent = parent.parent()

    def refresh_value_input(self):
        if self.mode_combo.currentText() == AFFIX_PERCENT_MODE:
            self.value_edit.setPlaceholderText("Percent (0-100)")
            self.value_edit.setValidator(QIntValidator(0, 100, self.value_edit))
            display_value = (
                "" if self.unique_aspect.min_percent_of_aspect == 0 else str(self.unique_aspect.min_percent_of_aspect)
            )
        else:
            self.value_edit.setPlaceholderText("Value (optional)")
            self.value_edit.setValidator(QDoubleValidator(self.value_edit))
            display_value = "" if self.unique_aspect.value is None else str(self.unique_aspect.value)

        with QSignalBlocker(self.value_edit):
            self.value_edit.setText(display_value)

    def update_mode(self, current_text=None):
        mode = current_text or self.mode_combo.currentText()
        if mode == AFFIX_PERCENT_MODE:
            self.unique_aspect.value = None
        else:
            self.unique_aspect.min_percent_of_aspect = 0
        self.refresh_value_input()

    def update_value(self, value):
        if self.mode_combo.currentText() == AFFIX_PERCENT_MODE:
            try:
                percent = int(value) if value else 0
            except ValueError:
                return
            if not 0 <= percent <= 100:
                QMessageBox.warning(self, "Warning", "Min % must be between 0 and 100.")
                self.refresh_value_input()
                return
            self.unique_aspect.min_percent_of_aspect = percent
            self.unique_aspect.value = None
            return

        try:
            self.unique_aspect.value = float(value) if value else None
        except ValueError:
            return
        self.unique_aspect.min_percent_of_aspect = 0
