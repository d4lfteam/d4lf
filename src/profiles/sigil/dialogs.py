from typing import TYPE_CHECKING, override

from PyQt6.QtCore import QSettings, QSize, Qt
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

from src.game_data import SIGIL_RULE_TARGET_TYPES, SigilRules, SigilRuleTargetType
from src.profiles.editor.dialogs import IgnoreScrollWheelComboBox

if TYPE_CHECKING:
    from PyQt6.QtGui import QCloseEvent


def _selected_sigil_target_type(combo: QComboBox) -> SigilRuleTargetType:
    target_type = combo.currentText()
    if target_type == "dungeon":
        return "dungeon"
    if target_type == "affix":
        return "affix"
    msg = f"Unknown sigil rule target type: {target_type}"
    raise ValueError(msg)


class CreateSigil(QDialog):
    def __init__(self, whitelist_sigils: list[str], blacklist_sigils: list[str], parent=None):
        super().__init__(parent)

        self.whitelist_sigils = whitelist_sigils
        self.blacklist_sigils = blacklist_sigils
        self.settings = QSettings("d4lf", "profile_editor")

        self.setWindowTitle("Create Sigil")
        self.setMinimumSize(420, 220)
        self.resize(self.settings.value("create_sigil_size", QSize(420, 220)))

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.kind_label = QLabel("Kind:")
        self.kind_input = IgnoreScrollWheelComboBox()
        self.kind_input.addItems(SIGIL_RULE_TARGET_TYPES)
        self.kind_input.currentTextChanged.connect(self._populate_names)

        self.name_label = QLabel("Name:")
        self.name_input = IgnoreScrollWheelComboBox()
        self.name_input.setEditable(True)
        self.name_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        name_completer = self.name_input.completer()
        if name_completer is not None:
            name_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._populate_names()
        self.type_label = QLabel("Type: ")
        self.type_input = IgnoreScrollWheelComboBox()
        self.type_input.setEditable(True)
        self.type_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        type_completer = self.type_input.completer()
        if type_completer is not None:
            type_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.type_input.addItems(["whitelist", "blacklist"])
        self.form_layout.addRow(self.kind_label, self.kind_input)
        self.form_layout.addRow(self.name_label, self.name_input)
        self.form_layout.addRow(self.type_label, self.type_input)
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
        target = SigilRules.default().target(
            self.name_input.currentText(), target_type=_selected_sigil_target_type(self.kind_input), display=True
        )
        if self.type_input.currentText() == "whitelist" and target.name in self.whitelist_sigils:
            QMessageBox.warning(self, "Warning", "Sigil already exist in whitelist. You can modify the existing one.")
            return
        if self.type_input.currentText() == "blacklist" and target.name in self.blacklist_sigils:
            QMessageBox.warning(self, "Warning", "Sigil already exist in whitelist. You can modify the existing one.")
            return
        super().accept()

    def _populate_names(self):
        self.name_input.clear()
        targets = SigilRules.default().targets(_selected_sigil_target_type(self.kind_input))
        self.name_input.addItems([target.display for target in targets])

    def get_value(self):
        sigil_name = self.name_input.currentText()
        type_name = self.type_input.currentText()
        kind = _selected_sigil_target_type(self.kind_input)
        return sigil_name, type_name, kind

    @override
    def closeEvent(self, a0: QCloseEvent | None) -> None:
        self.settings.setValue("create_sigil_size", self.size())
        if a0 is not None:
            a0.accept()


class RemoveSigil(QDialog):
    def __init__(self, sigils: list[str], blacklist: bool = False, parent=None):
        super().__init__(parent)
        self.sigils = sigils
        if blacklist:
            self.setWindowTitle("Delete Blacklist Sigil")
            self.groupbox = QGroupBox("Blacklist")
        else:
            self.setWindowTitle("Delete Whitelist Sigil")
            self.groupbox = QGroupBox("Whitelist")
        self.setFixedSize(300, 300)

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area = QScrollArea(self)
        scroll_widget = QWidget(scroll_area)
        scrollable_layout = QVBoxLayout(scroll_widget)
        self.groupbox_layout = QVBoxLayout()

        label = QLabel("Select Sigils to delete:")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.groupbox_layout.addWidget(label)

        self.checkbox_list: list[QCheckBox] = []
        for sigil in self.sigils:
            checkbox = QCheckBox(SigilRules.default().target(sigil).display)
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

    def get_value(self):
        rules = SigilRules.default()
        return [
            rules.target(checkbox.text(), display=True).name for checkbox in self.checkbox_list if checkbox.isChecked()
        ]
