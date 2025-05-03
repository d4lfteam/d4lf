from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.config.models import SigilConditionModel, SigilFilterModel, SigilPriority
from src.dataloader import Dataloader
from src.gui.collapsible_widget import Container
from src.gui.dialog import CreateSigil, IgnoreScrollWheelComboBox, RemoveSigil


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
        self.name_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        affix_sigil_dict = {
            **Dataloader().affix_sigil_dict_all["minor"],
            **Dataloader().affix_sigil_dict_all["major"],
            **Dataloader().affix_sigil_dict_all["positive"],
        }
        self.name_combo.addItems(sorted(affix_sigil_dict.values()))
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

    def __init__(self, sigil_name: str, sigil: SigilConditionModel, whitelist: bool):
        super().__init__(sigil_name, True)
        self.sigil = sigil
        self.sigil_name = sigil_name
        self.whitelist = whitelist
        self.setup_ui()

    def setup_ui(self):
        container_layout = QVBoxLayout(self.contentWidget)
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        form_layout = QFormLayout()
        self.sigil_name_combo = IgnoreScrollWheelComboBox()
        self.sigil_name_combo.setEditable(True)
        self.sigil_name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.sigil_name_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.sigil_name_combo.addItems(sorted(Dataloader().affix_sigil_dict_all["dungeons"].values()))
        self.sigil_name_combo.setCurrentText(self.sigil_name)
        self.sigil_name_combo.setMaximumWidth(150)
        self.sigil_name_combo.currentIndexChanged.connect(self.update_sigil_dungeon)
        form_layout.addRow("Dungeon:", self.sigil_name_combo)

        comparison_label = QLabel("Condition")
        title_layout.addSpacing(100)
        title_layout.addWidget(comparison_label)
        self.condition_list = QListWidget()
        self.condition_list.setMinimumHeight(50)
        self.condition_list.setAlternatingRowColors(True)
        for condition in self.sigil.condition:
            if condition == "":
                continue
            self.add_condition_to_list(Dataloader().affix_sigil_dict[condition])

        condition_btn_layout = QHBoxLayout()
        add_condition_btn = QPushButton("Add Condition")
        add_condition_btn.clicked.connect(self.add_condition)
        condition_btn_layout.addWidget(add_condition_btn)
        remove_condition_btn = QPushButton("Remove Condition")
        remove_condition_btn.clicked.connect(self.remove_selected)
        condition_btn_layout.addWidget(remove_condition_btn)
        layout.addLayout(form_layout)
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
        self.add_condition_to_list(list(Dataloader().affix_sigil_dict_all["minor"].values())[0])
        self.sigil.condition.append(list(Dataloader().affix_sigil_dict_all["minor"].keys())[0])

    def remove_selected(self):
        for item in self.condition_list.selectedItems():
            row = self.condition_list.row(item)
            self.condition_list.takeItem(row)
            self.sigil.condition.pop(row)

    def revert_sigil_dungeon(self):
        self.sigil_name_combo.currentIndexChanged.disconnect()
        self.sigil_name_combo.currentTextChanged.connect(lambda: self.update_sigil_dungeon(False))
        self.sigil_name_combo.setCurrentText(self.old_name)
        self.sigil_name_combo.currentTextChanged.disconnect()
        self.sigil_name_combo.currentIndexChanged.connect(self.update_sigil_dungeon)

    def update_sigil_dungeon(self, classic=True):
        new_name = self.sigil_name_combo.currentText()
        self.old_name = self.sigil_name
        self.sigil_name = new_name
        self.header.set_name(new_name)
        reverse_dict = {v: k for k, v in Dataloader().affix_sigil_dict_all["dungeons"].items()}
        self.sigil.name = reverse_dict.get(new_name)
        if classic:
            self.dungeon_changed.emit()

    def on_condition_update(self, old_condition, condition: str):
        reverse_dict = {v: k for k, v in Dataloader().affix_sigil_dict.items()}
        index = self.sigil.condition.index(reverse_dict.get(old_condition, ""))
        self.sigil.condition.pop(index)
        self.sigil.condition.insert(index, reverse_dict.get(condition))


class SigilsTab(QWidget):
    def __init__(self, sigil_model: SigilFilterModel, parent=None):
        super().__init__(parent)
        if sigil_model == None:
            self.sigil_model = SigilFilterModel(blacklist=[], whitelist=[], priority=SigilPriority.whitelist)
        else:
            self.sigil_model = sigil_model

        self.setup_ui()

    def setup_ui(self):
        """Populate the grid layout with existing groups"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 20, 0, 20)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.create_button_layout()
        self.create_form()
        self.create_containers()

    def create_button_layout(self):
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

    def create_form(self):
        self.general_form = QFormLayout()
        self.priority_combobox = IgnoreScrollWheelComboBox()
        self.priority_combobox.setEditable(True)
        self.priority_combobox.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.priority_combobox.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.priority_combobox.addItems(SigilPriority._member_names_)
        self.priority_combobox.setCurrentText(self.sigil_model.priority)
        self.priority_combobox.setMaximumWidth(150)
        self.priority_combobox.currentIndexChanged.connect(self.update_priority)
        self.general_form.addRow("Priority:", self.priority_combobox)
        self.main_layout.addLayout(self.general_form)

    def create_containers(self):
        # Blacklist
        self.blacklist_container = Container("Blacklist")
        self.blacklist_layout = QVBoxLayout(self.blacklist_container.contentWidget)
        self.blacklist_sigils = []

        for sigil_condition in self.sigil_model.blacklist:
            self.add_sigil(sigil_condition)
            self.blacklist_sigils.append(Dataloader().affix_sigil_dict[sigil_condition.name])

        # Whitelist
        self.whitelist_container = Container("Whitelist")
        self.whitelist_layout = QVBoxLayout(self.whitelist_container.contentWidget)
        self.whitelist_sigils = []

        for sigil_condition in self.sigil_model.whitelist:
            self.add_sigil(sigil_condition, True)
            self.whitelist_sigils.append(Dataloader().affix_sigil_dict[sigil_condition.name])

        self.main_layout.addWidget(self.whitelist_container)
        self.main_layout.addWidget(self.blacklist_container)

    def add_sigil(self, sigil_condition: SigilConditionModel, whitelist: bool = False):
        name = Dataloader().affix_sigil_dict_all["dungeons"][sigil_condition.name]
        if whitelist:
            widget = SigilWidget(name, sigil_condition, True)
            widget.dungeon_changed.connect(lambda: self.on_dungeon_changed(widget))
            self.whitelist_layout.addWidget(widget)
        else:
            widget = SigilWidget(name, sigil_condition, False)
            widget.dungeon_changed.connect(lambda: self.on_dungeon_changed(widget))
            self.blacklist_layout.addWidget(widget)

    def create_sigil(self):
        dialog = CreateSigil(self.whitelist_sigils, self.blacklist_sigils)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            sigil_name, type_name = dialog.get_value()
            reverse_dict = {v: k for k, v in Dataloader().affix_sigil_dict_all["dungeons"].items()}
            sigil_condition = SigilConditionModel(name=reverse_dict.get(sigil_name), condition=[])
            if type_name == "whitelist":
                widget = SigilWidget(sigil_name, sigil_condition, True)
                widget.dungeon_changed.connect(lambda: self.on_dungeon_changed(widget))
                self.whitelist_layout.addWidget(widget)
                self.whitelist_sigils.append(sigil_name)
                self.sigil_model.whitelist.append(sigil_condition)
            elif type_name == "blacklist":
                widget = SigilWidget(sigil_name, sigil_condition, False)
                widget.dungeon_changed.connect(lambda: self.on_dungeon_changed(widget))
                self.blacklist_layout.addWidget(widget)
                self.blacklist_sigils.append(sigil_name)
                self.sigil_model.blacklist.append(sigil_condition)

    def remove_sigil(self, blacklist: bool = False):
        if blacklist:
            dialog = RemoveSigil(self.blacklist_sigils, blacklist=True)
        else:
            dialog = RemoveSigil(self.whitelist_sigils)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            to_delete = dialog.get_value()
            if blacklist:
                for sigil in to_delete:
                    self.blacklist_sigils.remove(sigil)
                to_delete_list = []
                for i in range(self.blacklist_layout.count()):
                    sigil_widget: SigilWidget = self.blacklist_layout.itemAt(i).widget()
                    if sigil_widget.sigil_name in to_delete:
                        to_delete_list.append(sigil_widget)
                for sig_widget in to_delete_list:
                    sig_widget.setParent(None)
                    self.sigil_model.blacklist.remove(sig_widget.sigil)
            else:
                for sigil in to_delete:
                    self.whitelist_sigils.remove(sigil)
                to_delete_list = []
                for i in range(self.whitelist_layout.count()):
                    sigil_widget: SigilWidget = self.whitelist_layout.itemAt(i).widget()
                    if sigil_widget.sigil_name in to_delete:
                        to_delete_list.append(sigil_widget)
                for sig_widget in to_delete_list:
                    sig_widget.setParent(None)
                    self.sigil_model.whitelist.remove(sig_widget.sigil)

    def update_priority(self):
        self.sigil_model.priority = SigilPriority(self.priority_combobox.currentText())

    def on_dungeon_changed(self, sigil_widget: SigilWidget):
        whitelist = sigil_widget.whitelist
        new_name = sigil_widget.sigil_name
        old_name = sigil_widget.old_name
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
