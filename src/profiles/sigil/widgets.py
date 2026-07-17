from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.item import Dataloader, SigilRules, SigilRuleTargetType
from src.profiles.editor import Container, IgnoreScrollWheelComboBox

if TYPE_CHECKING:
    from src.profiles import SigilConditionModel

SIGILS_TABNAME = "Sigils"


class ConditionWidget(QWidget):
    condition_changed = pyqtSignal(str, str)

    def __init__(self, condition: str, parent=None):
        super().__init__(parent)
        self.condition = condition
        widget_layout = QHBoxLayout()
        widget_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.name_combo = IgnoreScrollWheelComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        name_completer = self.name_combo.completer()
        if name_completer is not None:
            name_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.name_combo.addItems([target.display for target in SigilRules.default().targets("affix")])
        self.name_combo.setMaximumWidth(600)
        self.name_combo.setCurrentText(condition)
        self.name_combo.currentIndexChanged.connect(self.update_condition)
        widget_layout.addWidget(self.name_combo)
        self.setLayout(widget_layout)

    def update_condition(self):
        old_condition = self.condition
        self.condition = self.name_combo.currentText()
        self.condition_changed.emit(old_condition, self.condition)


class SigilWidget(Container):
    dungeon_changed = pyqtSignal()

    def __init__(
        self, sigil_name: str, sigil: SigilConditionModel, whitelist: bool, kind: SigilRuleTargetType = "dungeon"
    ):
        super().__init__(sigil_name, color_background=True)
        self.sigil = sigil
        self.sigil_name = sigil_name
        self.whitelist = whitelist
        self.kind = kind
        self.setup_ui()

    def setup_ui(self):
        container_layout = QVBoxLayout(self.content_widget)
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        form_layout = QFormLayout()
        self.sigil_name_combo = IgnoreScrollWheelComboBox()
        self.sigil_name_combo.setEditable(True)
        self.sigil_name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        name_completer = self.sigil_name_combo.completer()
        if name_completer is not None:
            name_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.sigil_name_combo.addItems([target.display for target in SigilRules.default().targets(self.kind)])
        self.sigil_name_combo.setCurrentText(self.sigil_name)
        self.sigil_name_combo.setMaximumWidth(150)
        self.sigil_name_combo.currentIndexChanged.connect(self.update_sigil_dungeon)
        form_layout.addRow("Affix:" if self.kind == "affix" else "Dungeon:", self.sigil_name_combo)

        layout.addLayout(form_layout)
        comparison_label = QLabel("Condition")
        title_layout.addSpacing(100)
        title_layout.addWidget(comparison_label)
        self.condition_list = QListWidget()
        self.condition_list.setMinimumHeight(50)
        self.condition_list.setAlternatingRowColors(True)
        for condition in self.sigil.condition:
            if not condition:
                continue
            self.add_condition_to_list(Dataloader().affix_sigil_dict[condition])

        condition_btn_layout = QHBoxLayout()
        add_condition_btn = QPushButton("Add Condition")
        add_condition_btn.clicked.connect(self.add_condition)
        condition_btn_layout.addWidget(add_condition_btn)
        remove_condition_btn = QPushButton("Remove Condition")
        remove_condition_btn.clicked.connect(self.remove_selected)
        condition_btn_layout.addWidget(remove_condition_btn)

        layout.addLayout(condition_btn_layout)
        layout.addLayout(title_layout)
        layout.addWidget(self.condition_list)
        widget.setLayout(layout)
        container_layout.addWidget(widget)

    def add_condition_to_list(self, condition):
        widget_item = QListWidgetItem()
        widget = ConditionWidget(condition)
        widget.condition_changed.connect(self.on_condition_update)
        widget_item.setSizeHint(widget.sizeHint())
        self.condition_list.addItem(widget_item)
        self.condition_list.setItemWidget(widget_item, widget)

    def add_condition(self):
        minor_dict = Dataloader().affix_sigil_dict_all.get("minor", {})
        default_val = next(iter(minor_dict.values()), "")
        default_key = next(iter(minor_dict.keys()), "")
        self.add_condition_to_list(default_val)
        self.sigil.condition.append(default_key)

    def remove_selected(self):
        for item in self.condition_list.selectedItems():
            row = self.condition_list.row(item)
            self.condition_list.takeItem(row)
            self.sigil.condition.pop(row)

    def revert_sigil_dungeon(self):
        self.sigil_name_combo.currentIndexChanged.disconnect()
        self.sigil_name_combo.currentTextChanged.connect(lambda: self.update_sigil_dungeon(classic=False))
        self.sigil_name_combo.setCurrentText(self.old_name)
        self.sigil_name_combo.currentTextChanged.disconnect()
        self.sigil_name_combo.currentIndexChanged.connect(self.update_sigil_dungeon)

    def update_sigil_dungeon(self, classic=True):
        new_name = self.sigil_name_combo.currentText()
        self.old_name = self.sigil_name
        self.sigil_name = new_name
        self.header.set_name(new_name)
        self.sigil.name = SigilRules.default().target(new_name, target_type=self.kind, display=True).name
        if classic:
            self.dungeon_changed.emit()

    def on_condition_update(self, old_condition, condition: str):
        sigil_rules = SigilRules.default()
        old_target = sigil_rules.target(old_condition, target_type="affix", display=True)
        new_target = sigil_rules.target(condition, target_type="affix", display=True)
        index = self.sigil.condition.index(old_target.name)
        self.sigil.condition.pop(index)
        self.sigil.condition.insert(index, new_target.name)
