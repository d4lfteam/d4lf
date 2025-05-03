from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.config.models import AffixFilterModel, AspectUniqueFilterModel, ComparisonType, ItemType, UniqueModel
from src.dataloader import Dataloader
from src.gui.affixes_tab import AffixWidget
from src.gui.dialog import DeleteItem, IgnoreScrollWheelComboBox, IgnoreScrollWheelSpinBox, MinGreaterDialog, MinPowerDialog
from src.item.data.item_type import is_armor, is_jewelry, is_weapon


class UniqueWidget(QWidget):
    def __init__(self, unique_model: UniqueModel, parent=None):
        super().__init__(parent)
        self.unique_model = unique_model

        self.setup_ui()

    def setup_ui(self):
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        # Content widget that will hold all our existing UI elements
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.create_general_groupbox()

        if self.unique_model.aspect:
            self.create_aspect_groupbox()

        if self.unique_model.affix != []:
            self.create_affix_groupbox()

        # Set up scroll area
        scroll_area.setWidget(content_widget)
        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_layout.addWidget(scroll_area)
        self.setLayout(self.main_layout)

    def create_general_groupbox(self):
        # General Settings
        self.general_groupbox = QGroupBox()
        self.general_groupbox.setTitle("General Infos")
        self.general_form = QFormLayout()

        self.create_item_type_combobox()

        self.min_power = IgnoreScrollWheelSpinBox()
        self.min_power.setMaximum(800)
        self.min_power.setValue(self.unique_model.minPower)
        self.min_power.setMaximumWidth(150)
        self.min_power.valueChanged.connect(self.update_min_power)
        self.general_form.addRow("Minimum Power:", self.min_power)

        self.min_greater = IgnoreScrollWheelSpinBox()
        self.min_greater.setValue(self.unique_model.minGreaterAffixCount)
        self.min_greater.setMaximumWidth(150)
        self.min_greater.valueChanged.connect(self.update_min_greater_affix)
        self.general_form.addRow("Min Greater Affixes:", self.min_greater)

        self.min_percent = IgnoreScrollWheelSpinBox()
        self.min_percent.setValue(self.unique_model.minPercentOfAspect)
        self.min_percent.setMaximum(100)
        self.min_percent.setMaximumWidth(150)
        self.min_percent.valueChanged.connect(self.update_min_percent)
        self.general_form.addRow("Min Percent of Aspect:", self.min_percent)

        self.mythic = QCheckBox()
        self.mythic.checkStateChanged.connect(self.update_mythic)
        self.general_form.addRow("Mythic:", self.mythic)
        self.general_groupbox.setLayout(self.general_form)
        self.content_layout.addWidget(self.general_groupbox)

    def create_item_type_combobox(self):
        self.item_type_combo = IgnoreScrollWheelComboBox()
        self.item_type_combo.setEditable(True)
        self.item_type_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.item_type_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        item_types_names = [item.name for item in ItemType.__members__.values() if is_armor(item) or is_jewelry(item) or is_weapon(item)]
        item_types_names.append("None")
        self.item_type_combo.addItems(item_types_names)
        if len(self.unique_model.itemType) == 0:
            self.item_type_combo.setCurrentText("None")
        else:
            self.item_type_combo.setCurrentText(self.unique_model.itemType[0].name)
        self.item_type_combo.setMaximumWidth(150)
        self.item_type_combo.currentIndexChanged.connect(self.update_item_type)
        self.general_form.addRow("Item Type:", self.item_type_combo)

    def create_aspect_groupbox(self):
        # Aspect settings
        self.unique_aspect_groupbox = QGroupBox()
        self.unique_aspect_groupbox.setTitle("Aspect")
        self.unique_aspect_form = QFormLayout()
        self.unique_aspect_groupbox.setMinimumWidth(900)

        self.aspect_name_combo = IgnoreScrollWheelComboBox()
        self.aspect_name_combo.setEditable(True)

        self.aspect_name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.aspect_name_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.aspect_name_combo.addItems(sorted(Dataloader().aspect_unique_dict.keys()))
        self.aspect_name_combo.setCurrentText(self.unique_model.aspect.name)
        self.aspect_name_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.aspect_name_combo.setMinimumWidth(600)
        self.aspect_name_combo.currentIndexChanged.connect(self.update_aspect_name)
        self.unique_aspect_form.addRow("Name:", self.aspect_name_combo)

        # Value Input
        self.aspect_value_edit = QLineEdit()
        self.aspect_value_edit.setMaximumWidth(100)
        self.aspect_value_edit.setPlaceholderText("Value (optional)")
        if self.unique_model.aspect.value is not None:
            self.aspect_value_edit.setText(str(self.unique_model.aspect.value))
        self.aspect_value_edit.textChanged.connect(self.update_aspect_value)
        self.unique_model.aspect.value = self.unique_model.aspect.value
        self.unique_aspect_form.addRow("Value:", self.aspect_value_edit)
        # Comparison Combobox
        self.comparison_combo = IgnoreScrollWheelComboBox()
        self.comparison_combo.setEditable(True)
        self.comparison_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.comparison_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.comparison_combo.setMaximumWidth(100)
        self.comparison_combo.addItems([ct.value for ct in ComparisonType])
        self.comparison_combo.setCurrentText(self.unique_model.aspect.comparison.value)
        self.comparison_combo.currentIndexChanged.connect(self.update_aspect_comparison)
        self.unique_model.aspect.comparison = ComparisonType(self.unique_model.aspect.comparison.value)
        self.unique_aspect_form.addRow("Comparison:", self.comparison_combo)
        self.unique_aspect_groupbox.setLayout(self.unique_aspect_form)
        self.content_layout.insertWidget(1, self.unique_aspect_groupbox)
        # self.content_layout.addWidget(self.unique_aspect_groupbox)

    def remove_aspect_groupbox(self):
        self.unique_aspect_groupbox.setParent(None)

    def create_affix_groupbox(self):
        self.affix_groupbox = QGroupBox()
        self.affix_groupbox.setTitle("Affixes")
        self.affix_groupbox_layout = QVBoxLayout()

        self.affix_list = QListWidget()
        self.affix_list.setMinimumHeight(200)
        self.affix_list.setAlternatingRowColors(True)
        for affix in self.unique_model.affix:
            self.add_affix_item(affix)

        affix_btn_layout = QHBoxLayout()
        add_affix_btn = QPushButton("Add Affix")
        add_affix_btn.clicked.connect(self.add_affix)
        affix_btn_layout.addWidget(add_affix_btn)
        remove_affix_btn = QPushButton("Remove Affix")
        remove_affix_btn.clicked.connect(self.remove_affix)
        affix_btn_layout.addWidget(remove_affix_btn)
        self.affix_groupbox_layout.addLayout(affix_btn_layout)
        self.affix_groupbox_layout.addWidget(self.affix_list)
        self.affix_groupbox.setLayout(self.affix_groupbox_layout)
        self.content_layout.addWidget(self.affix_groupbox)

    def remove_affix_groupbox(self):
        self.affix_groupbox.setParent(None)

    def add_affix_item(self, affix: AffixFilterModel):
        item = QListWidgetItem()
        widget = AffixWidget(affix)
        item.setSizeHint(widget.sizeHint())
        self.affix_list.addItem(item)
        self.affix_list.setItemWidget(item, widget)

    def add_affix(self):
        new_affix = AffixFilterModel(name=list(Dataloader().affix_dict.keys())[0], value=None, comparison=ComparisonType.larger)
        self.unique_model.affix.append(new_affix)
        self.add_affix_item(new_affix)

    def remove_affix(self):
        for item in self.affix_list.selectedItems():
            row = self.affix_list.row(item)
            self.affix_list.takeItem(row)
            del self.unique_model.affix[row]

    def update_item_type(self):
        if self.item_type_combo.currentText() == "None":
            self.unique_model.itemType = []
        else:
            self.unique_model.itemType = [ItemType(ItemType._member_map_[self.item_type_combo.currentText()])]

    def update_min_power(self):
        self.unique_model.minPower = self.min_power.value()

    def update_min_greater_affix(self):
        self.unique_model.minGreaterAffixCount = self.min_greater.value()

    def update_min_percent(self):
        self.unique_model.minPercentOfAspect = self.min_percent.value()

    def update_mythic(self):
        self.unique_model.mythic = self.mythic.isChecked()

    def update_aspect_name(self):
        self.unique_model.aspect.name = self.aspect_name_combo.currentText()

    def update_aspect_value(self, value):
        try:
            self.unique_model.aspect.value = float(value) if value else None
        except ValueError:
            return

    def update_aspect_comparison(self):
        comparison = self.comparison_combo.currentText()
        self.unique_model.aspect.comparison = ComparisonType(comparison)


class UniquesTab(QWidget):
    def __init__(self, unique_model_list: list[UniqueModel], parent=None):
        super().__init__(parent)
        self.unique_model_list = unique_model_list
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 20, 0, 20)
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        self.add_button = QToolButton()
        self.add_button.setText("+")
        self.add_button.clicked.connect(self.add_item_type)

        self.tab_widget.setCornerWidget(self.add_button)
        self.toolbar = QToolBar("MyToolBar", self)
        self.toolbar.setMinimumHeight(50)
        self.toolbar.setContentsMargins(10, 10, 10, 10)
        self.toolbar.setMovable(False)
        for i, unique_model in enumerate(self.unique_model_list):
            group = UniqueWidget(unique_model)
            self.tab_widget.addTab(group, f"Unique {i}")
        # Add buttons to toolbar
        add_item_button = QPushButton("Create Unique")
        remove_item_button = QPushButton("Remove Unique")
        add_aspect_button = QPushButton("Add Aspect to current unique")
        remove_aspect_button = QPushButton("Remove Aspect to current unique")
        add_affixes_button = QPushButton("Add Affixes to current unique")
        remove_affixes_button = QPushButton("Remove Affixes to current unique")
        set_all_minGreaterAffix_button = QPushButton("Set all minGreaterAffix")
        set_all_minPower_button = QPushButton("Set all minPower")
        add_item_button.clicked.connect(self.add_item_type)
        remove_item_button.clicked.connect(self.remove_item_type)
        add_aspect_button.clicked.connect(self.add_aspect_to_current_unique)
        add_affixes_button.clicked.connect(self.add_affixes_to_current_unique)
        remove_aspect_button.clicked.connect(self.remove_aspect_from_current_unique)
        remove_affixes_button.clicked.connect(self.remove_affixes_from_current_unique)
        set_all_minGreaterAffix_button.clicked.connect(self.set_all_minGreaterAffix)
        set_all_minPower_button.clicked.connect(self.set_all_minPower)
        self.toolbar.addWidget(add_item_button)
        self.toolbar.addWidget(remove_item_button)
        self.toolbar.addWidget(add_aspect_button)
        self.toolbar.addWidget(remove_aspect_button)
        self.toolbar.addWidget(add_affixes_button)
        self.toolbar.addWidget(remove_affixes_button)
        self.toolbar.addWidget(set_all_minGreaterAffix_button)
        self.toolbar.addWidget(set_all_minPower_button)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addWidget(self.tab_widget)

    def close_tab(self, index):
        self.tab_widget.removeTab(index)
        self.unique_model_list.pop(index)
        self.rename_tabs()

    def remove_item_type(self):
        dialog = DeleteItem([self.tab_widget.tabText(i) for i in range(self.tab_widget.count())], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item_names_to_delete = dialog.get_value()
            to_delete_index = [i for i in range(self.tab_widget.count()) if self.tab_widget.tabText(i) in item_names_to_delete]
            to_delete_index.reverse()
            for index in to_delete_index:
                self.tab_widget.removeTab(index)
                self.unique_model_list.pop(index)
            self.rename_tabs()
            return

    def rename_tabs(self):
        for i in range(self.tab_widget.count()):
            self.tab_widget.setTabText(i, f"Unique {i}")

    def add_item_type(self):
        unique_model = UniqueModel()
        group = UniqueWidget(unique_model)
        self.tab_widget.addTab(group, f"Unique {self.tab_widget.count()}")
        self.unique_model_list.append(unique_model)

    def add_aspect_to_current_unique(self):
        current_unique: UniqueWidget = self.tab_widget.currentWidget()
        if current_unique.unique_model.aspect:
            QMessageBox.warning(self, "Warn", "An aspect already exist for the current unique. Please modify the existing one.")
        else:
            current_unique.unique_model.aspect = AspectUniqueFilterModel(name=sorted(Dataloader().aspect_unique_dict.keys())[0])
            current_unique.create_aspect_groupbox()

    def add_affixes_to_current_unique(self):
        current_unique: UniqueWidget = self.tab_widget.currentWidget()
        if current_unique.unique_model.affix:
            QMessageBox.warning(self, "Warn", "An affix already exist for the current unique. Please modify the existing one.")
        else:
            current_unique.unique_model.affix = [AffixFilterModel(name=sorted(Dataloader().affix_dict.keys())[0])]
            current_unique.create_affix_groupbox()

    def remove_aspect_from_current_unique(self):
        current_unique: UniqueWidget = self.tab_widget.currentWidget()
        if not current_unique.unique_model.aspect:
            QMessageBox.warning(self, "Warn", "There is no aspect in the current unique. You can add one.")
        else:
            current_unique.unique_model.aspect = None
            current_unique.remove_aspect_groupbox()

    def remove_affixes_from_current_unique(self):
        current_unique: UniqueWidget = self.tab_widget.currentWidget()
        if not current_unique.unique_model.affix:
            QMessageBox.warning(self, "Warn", "There is no affix in the current unique. You can add one.")
        else:
            current_unique.unique_model.affix = []
            current_unique.remove_affix_groupbox()

    def set_all_minGreaterAffix(self):
        dialog = MinGreaterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            minGreaterAffix = dialog.get_value()
            for i in range(self.tab_widget.count()):
                tab: UniqueWidget = self.tab_widget.widget(i)
                tab.min_greater.setValue(minGreaterAffix)
                tab.update_min_greater_affix()

    def set_all_minPower(self):
        dialog = MinPowerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            minPower = dialog.get_value()
            for i in range(self.tab_widget.count()):
                tab: UniqueWidget = self.tab_widget.widget(i)
                tab.min_power.setValue(minPower)
                tab.update_min_power()
