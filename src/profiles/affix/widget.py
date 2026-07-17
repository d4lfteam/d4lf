from typing import Protocol, runtime_checkable

from PyQt6.QtCore import QSignalBlocker, Qt
from PyQt6.QtGui import QDoubleValidator, QIntValidator
from PyQt6.QtWidgets import QCheckBox, QComboBox, QCompleter, QHBoxLayout, QLineEdit, QMessageBox, QWidget

from src.item import Dataloader
from src.profiles import AffixFilterModel, SealFilterModel
from src.profiles.affix.helpers import affix_dict_for_widget, get_affixes_for_set, get_set_and_base_for_key
from src.profiles.editor import IgnoreScrollWheelComboBox

AFFIXES_TABNAME = "Affixes"
AFFIX_VALUE_MODE = "Value"
AFFIX_PERCENT_MODE = "Min %"
UNIQUE_ASPECTS_TITLE = "Unique Aspects"


@runtime_checkable
class GreaterCountParent(Protocol):
    def update_greater_count_label(self) -> None: ...

    def sync_min_greater_from_checkboxes(self) -> None: ...


class AffixWidget(QWidget):
    def __init__(self, affix: AffixFilterModel, parent=None):
        super().__init__(parent)
        self.affix = affix
        self.filtered_affixes: dict[str, str] = {}
        self.setup_ui()

    def get_parent_seal_config(self):
        curr = self
        while curr:
            config = getattr(curr, "config", None)
            if isinstance(config, SealFilterModel):
                return config
            curr = curr.parent()
        return None

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.setSpacing(50)

        is_seal = self.get_parent_seal_config() is not None

        if is_seal:
            self.create_set_name_combobox()
            layout.addWidget(self.set_combo)

        self.create_affix_name_combobox()
        self.create_greater_checkbox()
        self.create_mode_combobox()
        self.create_value_input()
        self.mode_combo.currentTextChanged.connect(self.update_mode)
        self.update_mode(self.mode_combo.currentText())

        layout.addWidget(self.name_combo)
        layout.addWidget(self.greater_checkbox)
        layout.addWidget(self.mode_combo)
        layout.addWidget(self.value_edit)

        self.setLayout(layout)

    def get_affix_dict(self):
        return affix_dict_for_widget(self)

    def create_set_name_combobox(self):
        self.set_combo = IgnoreScrollWheelComboBox()
        self.set_combo.setFixedWidth(200)
        self.set_combo.addItems(["(No Set Selected)"] + sorted(Dataloader().set_list))

        curr_set, _ = get_set_and_base_for_key(self.affix.name, Dataloader().set_list)
        if curr_set:
            self.set_combo.setCurrentText(curr_set)
        else:
            self.set_combo.setCurrentText("(No Set Selected)")

        self.set_combo.currentTextChanged.connect(self.on_set_changed)

    def on_set_changed(self):
        self.populate_affix_combo()
        if self.name_combo.count() > 0:
            self.name_combo.setCurrentIndex(0)
            self.update_name()

    def populate_affix_combo(self):
        _blocker = QSignalBlocker(self.name_combo)
        self.name_combo.clear()

        is_seal = self.get_parent_seal_config() is not None
        affix_dict = self.get_affix_dict()

        if is_seal:
            selected_set = self.set_combo.currentText()
            target_set = None if selected_set == "(No Set Selected)" else selected_set

            self.filtered_affixes = get_affixes_for_set(affix_dict, Dataloader().set_list, target_set)
            self.name_combo.addItems(sorted(self.filtered_affixes.values()))

            curr_set, _ = get_set_and_base_for_key(self.affix.name, Dataloader().set_list)
            if curr_set == target_set and self.affix.name in self.filtered_affixes:
                self.name_combo.setCurrentText(self.filtered_affixes[self.affix.name])
            else:
                if self.filtered_affixes:
                    first_text = min(self.filtered_affixes.values())
                    self.name_combo.setCurrentText(first_text)
                else:
                    self.name_combo.setCurrentText("")
                reverse_dict = {v: k for k, v in self.filtered_affixes.items()}
                self.affix.name = reverse_dict.get(self.name_combo.currentText(), "")
        else:
            self.name_combo.addItems(sorted(affix_dict.values()))
            if self.affix.name in affix_dict:
                self.name_combo.setCurrentText(affix_dict[self.affix.name])

    def create_affix_name_combobox(self):
        self.name_combo = IgnoreScrollWheelComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        name_completer = self.name_combo.completer()
        if name_completer is not None:
            name_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            name_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.name_combo.setMaximumWidth(600)
        self.populate_affix_combo()
        # currentIndexChanged misses some editable-combobox keyboard flows.
        self.name_combo.currentTextChanged.connect(self.update_name)

    def create_greater_checkbox(self):
        self.greater_checkbox = QCheckBox("Greater")
        self.greater_checkbox.setChecked(getattr(self.affix, "want_greater", False))
        self.greater_checkbox.setFixedWidth(80)
        self.greater_checkbox.setProperty("greaterCheckbox", True)  # ruff:ignore[boolean-positional-value-in-call]
        self._refresh_widget_style(self.greater_checkbox)
        self.greater_checkbox.stateChanged.connect(self.update_greater)
        self.greater_checkbox.stateChanged.connect(self.update_parent_count_label)

    def _refresh_widget_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def update_parent_count_label(self):
        parent = self.parent()
        while parent:
            if isinstance(parent, GreaterCountParent):
                parent.update_greater_count_label()
                parent.sync_min_greater_from_checkboxes()
                break
            parent = parent.parent()

    def create_mode_combobox(self):
        self.mode_combo = IgnoreScrollWheelComboBox()
        self.mode_combo.setFixedSize(100, self.mode_combo.sizeHint().height())
        self.mode_combo.addItems([AFFIX_VALUE_MODE, AFFIX_PERCENT_MODE])
        if self.affix.min_percent_of_affix:
            self.mode_combo.setCurrentText(AFFIX_PERCENT_MODE)
        else:
            self.mode_combo.setCurrentText(AFFIX_VALUE_MODE)

    def create_value_input(self):
        self.value_edit = QLineEdit()
        self.value_edit.setFixedSize(100, self.value_edit.sizeHint().height())
        self.value_edit.textChanged.connect(self.update_value)

    def update_name(self, current_text=None):
        """Update the model only when the editable combobox contains a valid affix."""
        is_seal = self.get_parent_seal_config() is not None
        affix_dict = self.get_affix_dict()
        text = current_text or self.name_combo.currentText()

        if is_seal:
            reverse_dict = {v: k for k, v in self.filtered_affixes.items()}
            self.affix.name = reverse_dict.get(text, "")
        else:
            reverse_dict = {v: k for k, v in affix_dict.items()}
            self.affix.name = reverse_dict.get(text, "")

    def refresh_value_input(self):
        if self.mode_combo.currentText() == AFFIX_PERCENT_MODE:
            self.value_edit.setPlaceholderText("Percent (0-100)")
            self.value_edit.setValidator(QIntValidator(0, 100, self.value_edit))
            display_value = "" if self.affix.min_percent_of_affix == 0 else str(self.affix.min_percent_of_affix)
        else:
            self.value_edit.setPlaceholderText("Value (optional)")
            self.value_edit.setValidator(QDoubleValidator(self.value_edit))
            display_value = "" if self.affix.value is None else str(self.affix.value)

        with QSignalBlocker(self.value_edit):
            self.value_edit.setText(display_value)

    def update_mode(self, current_text=None):
        mode = current_text or self.mode_combo.currentText()
        if mode == AFFIX_PERCENT_MODE:
            self.affix.value = None
        else:
            self.affix.min_percent_of_affix = 0
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
            self.affix.min_percent_of_affix = percent
            self.affix.value = None
            return

        try:
            self.affix.value = float(value) if value else None
        except ValueError:
            return
        self.affix.min_percent_of_affix = 0

    def update_greater(self):
        self.affix.want_greater = self.greater_checkbox.isChecked()

    def set_min_percent(self, percent: int, convert_mode: bool = False):
        if convert_mode and self.mode_combo.currentText() != AFFIX_PERCENT_MODE:
            self.mode_combo.setCurrentText(AFFIX_PERCENT_MODE)
        if self.mode_combo.currentText() != AFFIX_PERCENT_MODE:
            return
        self.value_edit.setText(str(percent))
