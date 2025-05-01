from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QDialog, QPushButton, QFormLayout, QHBoxLayout, QListWidget, QListWidgetItem, QLabel)
from PyQt6.QtCore import Qt
from src.config.models import SigilPriority, SigilFilterModel, SigilConditionModel
from src.gui.dialog import IgnoreScrollWheelComboBox, CreateSigil
from src.gui.collapsible_widget import Container
from src.dataloader import Dataloader

class SigilsTab(QWidget):
    def __init__(self, sigil_model: SigilFilterModel, parent=None):
        super().__init__(parent)
        self.sigil_model = sigil_model
        self.setup_ui()

    def setup_ui(self):
        """Populate the grid layout with existing groups"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 20, 0, 20)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.create_form()
        self.create_containers()

    def create_form(self):
        self.general_form = QFormLayout()
        self.priority_combobox = IgnoreScrollWheelComboBox()
        self.priority_combobox.addItems(SigilPriority._member_names_)
        self.priority_combobox.setCurrentText(self.sigil_model.priority)
        self.priority_combobox.setMaximumWidth(150)
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

        btn_layout = QHBoxLayout()
        add_sigil_btn = QPushButton("Add Sigil")
        remove_sigil_btn = QPushButton("Remove Sigil")
        add_sigil_btn.clicked.connect(self.create_sigil)

        btn_layout.addWidget(add_sigil_btn)
        btn_layout.addWidget(remove_sigil_btn)
        self.main_layout.addWidget(self.blacklist_container)
        self.main_layout.addWidget(self.whitelist_container)
        self.main_layout.addLayout(btn_layout)

    def add_sigil(self, sigil_condition : SigilConditionModel, whitelist : bool = False):
        name = Dataloader().affix_sigil_dict_all['dungeons'][sigil_condition.name]
        container = Container(name, True)
        container_layout = QVBoxLayout(container.contentWidget)
        widget = SigilWidget(sigil_condition)
        container_layout.addWidget(widget)
        if whitelist:
            self.whitelist_layout.addWidget(container)
        else:
            self.blacklist_layout.addWidget(container)

    def create_sigil(self):
        sigil_list = self.whitelist_sigils + self.blacklist_sigils
        dialog = CreateSigil(sigil_list)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            sigil_name, type_name = dialog.get_value()
            container = Container(sigil_name, True)
            container_layout = QVBoxLayout(container.contentWidget)
            reverse_dict = {v: k for k, v in Dataloader().affix_sigil_dict_all['dungeons'].items()}
            sigil_condition = SigilConditionModel(name=reverse_dict.get(sigil_name), condition=[])
            widget = SigilWidget(sigil_condition)
            container_layout.addWidget(widget)
            if type_name == 'whitelist':
                self.whitelist_layout.addWidget(container)
                self.whitelist_sigils.append(sigil_name)
            elif type_name == 'blacklist':
                self.blacklist_layout.addWidget(container)
                self.blacklist_sigils.append(sigil_name)

class SigilWidget(QWidget):
    def __init__(self, sigil : SigilConditionModel, parent=None):
        super().__init__(parent)
        self.sigil = sigil
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        comparison_label = QLabel("Condition")
        title_layout.addSpacing(100)
        title_layout.addWidget(comparison_label)
        self.condition_list = QListWidget()
        self.condition_list.setMinimumHeight(50)
        self.condition_list.setAlternatingRowColors(True)
        for condition in self.sigil.condition:
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
        self.setLayout(layout)

    def add_condition_to_list(self, condition):
        widget_item = QListWidgetItem()
        widget = ConditionWidget(condition)
        widget_item.setSizeHint(widget.sizeHint())
        self.condition_list.addItem(widget_item)
        self.condition_list.setItemWidget(widget_item, widget)

    def add_condition(self):
        self.add_condition_to_list(list(Dataloader().affix_sigil_dict_all['minor'].values())[0])

    def remove_selected(self):
        for item in self.condition_list.selectedItems():
            row = self.condition_list.row(item)
            self.condition_list.takeItem(row)

class ConditionWidget(QWidget):
    def __init__(self, condition : str, parent = None):
        super().__init__(parent)
        widget_layout = QHBoxLayout()
        widget_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        name_combo = IgnoreScrollWheelComboBox()
        name_combo.addItems(sorted(Dataloader().affix_sigil_dict_all['minor'].values()))
        name_combo.addItems(sorted(Dataloader().affix_sigil_dict_all['major'].values()))
        name_combo.addItems(sorted(Dataloader().affix_sigil_dict_all['positive'].values()))
        name_combo.setMaximumWidth(600)
        name_combo.setCurrentText(condition)
        widget_layout.addWidget(name_combo)
        self.setLayout(widget_layout)