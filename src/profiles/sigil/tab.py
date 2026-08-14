from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.game_data import SigilRules
from src.profiles import SigilConditionModel, SigilFilterModel, SigilPriority
from src.profiles.editor.container import Container
from src.profiles.editor.dialogs import IgnoreScrollWheelComboBox
from src.profiles.editor.pickers import RarityPicker, rarity_summary
from src.profiles.sigil.dialogs import CreateSigil, RemoveSigil
from src.profiles.sigil.widgets import SigilWidget

SIGILS_TABNAME = "Sigils"


class SigilsTab(QWidget):
    def __init__(self, sigil_model: SigilFilterModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.sigil_model = sigil_model
        self.loaded = False

    def load(self) -> None:
        if not self.loaded:
            self.setup_ui()
            self.loaded = True

    def setup_ui(self) -> None:
        """Populate the grid layout with existing groups."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 20, 0, 20)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.create_button_layout()
        self.create_form()
        self.create_containers()

    def create_button_layout(self) -> None:
        btn_layout = QHBoxLayout()

        add_sigil_btn = QPushButton("Add Sigil")
        add_sigil_btn.clicked.connect(self.create_sigil)

        remove_whitelist_sigil_btn = QPushButton("Remove Whitelist Sigil")
        remove_whitelist_sigil_btn.clicked.connect(lambda: self.remove_sigil())

        remove_blacklist_sigil_btn = QPushButton("Remove Blacklist Sigil")
        remove_blacklist_sigil_btn.clicked.connect(lambda: self.remove_sigil(blacklist=True))

        btn_layout.addWidget(add_sigil_btn)
        btn_layout.addWidget(remove_whitelist_sigil_btn)
        btn_layout.addWidget(remove_blacklist_sigil_btn)
        self.main_layout.addLayout(btn_layout)

    def create_form(self) -> None:
        self.general_form = QFormLayout()
        self.priority_combobox = IgnoreScrollWheelComboBox()
        self.priority_combobox.setEditable(True)
        self.priority_combobox.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        priority_completer = self.priority_combobox.completer()
        if priority_completer is not None:
            priority_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.priority_combobox.addItems(SigilPriority._member_names_)
        self.priority_combobox.setCurrentText(self.sigil_model.priority)
        self.priority_combobox.setMaximumWidth(150)
        self.priority_combobox.currentIndexChanged.connect(self.update_priority)
        self.general_form.addRow("Priority:", self.priority_combobox)

        self.rarity_line_edit = QLineEdit()
        self.rarity_line_edit.setReadOnly(True)
        self.refresh_rarity_summary()
        rarity_layout = QHBoxLayout()
        rarity_layout.addWidget(self.rarity_line_edit)
        edit_rarities_btn = QPushButton("...")
        edit_rarities_btn.setMaximumWidth(40)
        edit_rarities_btn.clicked.connect(self.edit_rarities)
        rarity_layout.addWidget(edit_rarities_btn)
        rarity_layout.addStretch()
        self.general_form.addRow("Rarities:", rarity_layout)

        self.main_layout.addLayout(self.general_form)

    def create_containers(self) -> None:
        # Blacklist
        self.blacklist_container = Container("Blacklist")
        self.blacklist_layout = QVBoxLayout(self.blacklist_container.content_widget)
        self.blacklist_sigils = []

        for sigil_condition in self.sigil_model.blacklist:
            self.add_sigil(sigil_condition)
            self.blacklist_sigils.append(sigil_condition.name)

        # Whitelist
        self.whitelist_container = Container("Whitelist")
        self.whitelist_layout = QVBoxLayout(self.whitelist_container.content_widget)
        self.whitelist_sigils = []

        for sigil_condition in self.sigil_model.whitelist:
            self.add_sigil(sigil_condition, whitelist=True)
            self.whitelist_sigils.append(sigil_condition.name)

        self.main_layout.addWidget(self.whitelist_container)
        self.main_layout.addWidget(self.blacklist_container)

    def add_sigil(self, sigil_condition: SigilConditionModel, whitelist: bool = False) -> None:
        target = SigilRules.default().target(sigil_condition.name)
        kind = target.target_type
        name = target.display
        if whitelist:
            widget = SigilWidget(name, sigil_condition, whitelist=True, kind=kind)
            widget.dungeon_changed.connect(lambda: self.on_dungeon_changed(widget))
            self.whitelist_layout.addWidget(widget)
        else:
            widget = SigilWidget(name, sigil_condition, whitelist=False, kind=kind)
            widget.dungeon_changed.connect(lambda: self.on_dungeon_changed(widget))
            self.blacklist_layout.addWidget(widget)

    def create_sigil(self) -> None:
        dialog = CreateSigil(self.whitelist_sigils, self.blacklist_sigils)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            sigil_name, type_name, kind = dialog.get_value()
            target = SigilRules.default().target(sigil_name, target_type=kind, display=True)
            sigil_condition = SigilConditionModel(name=target.name, condition=[])
            if type_name == "whitelist":
                widget = SigilWidget(sigil_name, sigil_condition, whitelist=True, kind=kind)
                widget.dungeon_changed.connect(lambda: self.on_dungeon_changed(widget))
                self.whitelist_layout.addWidget(widget)
                self.whitelist_sigils.append(target.name)
                self.sigil_model.whitelist.append(sigil_condition)
            elif type_name == "blacklist":
                widget = SigilWidget(sigil_name, sigil_condition, whitelist=False, kind=kind)
                widget.dungeon_changed.connect(lambda: self.on_dungeon_changed(widget))
                self.blacklist_layout.addWidget(widget)
                self.blacklist_sigils.append(target.name)
                self.sigil_model.blacklist.append(sigil_condition)

    def remove_sigil(self, blacklist: bool = False) -> None:
        sigils = self.blacklist_sigils if blacklist else self.whitelist_sigils
        layout = self.blacklist_layout if blacklist else self.whitelist_layout
        rules = self.sigil_model.blacklist if blacklist else self.sigil_model.whitelist
        dialog = RemoveSigil(sigils, blacklist=blacklist)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            to_delete = set(dialog.get_value())
            sigils[:] = [sigil for sigil in sigils if sigil not in to_delete]
            for index in reversed(range(layout.count())):
                item = layout.itemAt(index)
                widget = item.widget() if item is not None else None
                if not isinstance(widget, SigilWidget) or widget.sigil.name not in to_delete:
                    continue
                layout.takeAt(index)
                widget.setParent(None)
                rules.remove(widget.sigil)

    def update_priority(self) -> None:
        self.sigil_model.priority = SigilPriority(self.priority_combobox.currentText())

    def refresh_rarity_summary(self) -> None:
        self.rarity_line_edit.setText(rarity_summary(self.sigil_model.rarities))

    def edit_rarities(self) -> None:
        picker = RarityPicker(self, self.sigil_model.rarities)
        if picker.exec() == QDialog.DialogCode.Accepted:
            self.sigil_model.rarities = picker.get_selected_rarities()
            self.refresh_rarity_summary()

    def on_dungeon_changed(self, sigil_widget: SigilWidget) -> None:
        whitelist = sigil_widget.whitelist
        new_name = sigil_widget.sigil.name
        old_name = sigil_widget.old_sigil_name
        if whitelist and new_name in self.whitelist_sigils:
            QMessageBox.warning(self, "Warning", "Sigil already exist in whitelist. You can modify the existing one.")
            sigil_widget.revert_sigil_dungeon()
            return
        if not whitelist and new_name in self.blacklist_sigils:
            QMessageBox.warning(self, "Warning", "Sigil already exist in blacklist. You can modify the existing one.")
            sigil_widget.revert_sigil_dungeon()
            return
        if whitelist and old_name in self.whitelist_sigils:
            index = self.whitelist_sigils.index(old_name)
            self.whitelist_sigils.pop(index)
            self.whitelist_sigils.insert(index, new_name)
        if not whitelist and old_name in self.blacklist_sigils:
            index = self.blacklist_sigils.index(old_name)
            self.blacklist_sigils.pop(index)
            self.blacklist_sigils.insert(index, new_name)
