from PyQt6.QtWidgets import (QWidget, QScrollArea, QVBoxLayout, QFormLayout,
                            QPushButton, QListWidget, QListWidgetItem, QHBoxLayout,
                            QLineEdit, QInputDialog, QTabWidget, QSizePolicy, QLabel, QFrame, QDialog)
from PyQt6.QtCore import Qt
from src.config.models import ItemType, AffixFilterModel, AffixFilterCountModel, ItemFilterModel, ComparisonType, ProfileModel, DynamicItemFilterModel
from src.dataloader import Dataloader
from src.gui.dialog import IgnoreScrollWheelComboBox, IgnoreScrollWheelSpinBox, DeleteAffixPool
from src.gui.collapsible_widget import Container

class AffixGroupEditor(QWidget):
    def __init__(self, item_name: str, item_type: ItemType, config: ItemFilterModel, parent=None):
        super().__init__(parent)
        self.item_name = item_name
        self.item_type = item_type
        self.config = config
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding,
                          QSizePolicy.Policy.MinimumExpanding)
        self.setup_ui()

    def setup_ui(self):

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Content widget that will hold all our existing UI elements
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # General Settings
        general_form = QFormLayout()
        self.item_type_combo = IgnoreScrollWheelComboBox()
        self.item_type_combo.addItems(ItemType.__members__)
        self.item_type_combo.setCurrentText(self.item_type.name)
        self.item_type_combo.setMaximumWidth(150)
        general_form.addRow("Item Type:", self.item_type_combo)
        self.min_power = IgnoreScrollWheelSpinBox()
        self.min_power.setMaximum(950)
        self.min_power.setValue(self.config.minPower)
        self.min_power.setMaximumWidth(150)
        general_form.addRow("Minimum Power:", self.min_power)

        self.min_greater = IgnoreScrollWheelSpinBox()
        self.min_greater.setMaximum(950)
        self.min_greater.setValue(self.config.minGreaterAffixCount)
        self.min_greater.setMaximumWidth(150)
        general_form.addRow("Min Greater Affixes:", self.min_greater)

        self.content_layout.addLayout(general_form)

        # Affix Pool
        self.affix_pool_container = Container("Affix Pool")
        self.affix_pool_layout = QVBoxLayout(self.affix_pool_container.contentWidget)

        for pool in self.config.affixPool:
            self.add_affix_pool_item(pool)

        # Inherent Pool
        self.inherent_pool_container = Container("Inherent Pool")
        self.inherent_pool_layout = QVBoxLayout(self.inherent_pool_container.contentWidget)

        for pool in self.config.inherentPool:
            self.add_affix_pool_item(pool, True)

        pool_btn_layout = QHBoxLayout()
        add_affix_pool_btn = QPushButton("Add Affix Pool")
        add_affix_pool_btn.clicked.connect(self.add_affix_pool)
        add_inherent_pool_btn = QPushButton("Add Inherent Pool")
        add_inherent_pool_btn.clicked.connect(self.add_inherent_pool)
        remove_affix_pool_btn = QPushButton("Remove Affix Pool")
        remove_affix_pool_btn.clicked.connect(lambda: self.remove_selected(self.affix_pool_layout))
        remove_inherent_pool_btn = QPushButton("Remove Inherent Pool")
        remove_inherent_pool_btn.clicked.connect(lambda: self.remove_selected(self.inherent_pool_layout))

        pool_btn_layout.addWidget(add_affix_pool_btn)
        pool_btn_layout.addWidget(add_inherent_pool_btn)
        pool_btn_layout.addWidget(remove_affix_pool_btn)
        pool_btn_layout.addWidget(remove_inherent_pool_btn)

        # Add widgets to content layout
        self.content_layout.addWidget(self.affix_pool_container)
        self.content_layout.addWidget(self.inherent_pool_container)
        self.content_layout.addLayout(pool_btn_layout)

        # Set up scroll area
        scroll_area.setWidget(content_widget)

        # Main layout for the widget
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    def add_affix_pool_item(self, pool: AffixFilterCountModel, inherent : bool = False):


        if inherent:
            nb_count = self.inherent_pool_layout.count()
            container = Container(f"Count {nb_count}", True)
            container_layout = QVBoxLayout(container.contentWidget)
            widget = AffixPoolWidget(pool)
            container_layout.addWidget(widget)
            self.inherent_pool_layout.addWidget(container)
        else:
            nb_count = self.affix_pool_layout.count()
            container = Container(f"Count {nb_count}", True)
            container_layout = QVBoxLayout(container.contentWidget)
            widget = AffixPoolWidget(pool)
            container_layout.addWidget(widget)
            self.affix_pool_layout.addWidget(container)

    def add_affix_pool(self):
        # Create a default valid affix
        default_affix = AffixFilterModel(
            name=list(Dataloader().affix_dict.keys())[0],  # First valid affix name
            value=None,
            comparison=ComparisonType.larger
        )

        new_pool = AffixFilterCountModel(
            count=[default_affix],  # Start with at least one valid affix
            minCount=1,
            maxCount=3,
            minGreaterAffixCount=0
        )
        self.config.affixPool.append(new_pool)
        self.add_affix_pool_item(new_pool)

    def add_inherent_pool(self):
        # Create a default valid affix
        default_affix = AffixFilterModel(
            name=list(Dataloader().affix_dict.keys())[0],  # First valid affix name
            value=None,
            comparison=ComparisonType.larger
        )

        new_pool = AffixFilterCountModel(
            count=[default_affix],  # Start with at least one valid affix
            minCount=1,
            maxCount=3,
            minGreaterAffixCount=0
        )
        self.config.affixPool.append(new_pool)
        self.add_affix_pool_item(new_pool, True)

    def remove_selected(self, layout_widget : QVBoxLayout, inherent : bool = False):
        nb_pool = layout_widget.count()
        dialog = DeleteAffixPool(nb_pool, inherent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            to_delete = dialog.get_value()
            to_delete_list = []
            for i in range(layout_widget.count()):
                item = layout_widget.itemAt(i)
                if item and item.widget() is not None:  # Check if the item is a widget
                    if item.widget().header.name in to_delete:
                        to_delete_list.append(item.widget())
            for widget in to_delete_list:
                widget.setParent(None)
            self.reorganized_pool(layout_widget)

    def reorganized_pool(self, layout_widget : QVBoxLayout):
        for i in range(layout_widget.count()):
                item = layout_widget.itemAt(i)
                if item and item.widget() is not None:  # Check if the item is a widget
                    item.widget().header.set_name(f"Count {i}")


    def save_config(self):
        self.config.minPower = self.min_power.value()
        self.config.minGreaterAffixCount = self.min_greater.value()

class AffixPoolWidget(QWidget):
    def __init__(self, pool: AffixFilterCountModel, parent=None):
        super().__init__(parent)
        self.pool = pool
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # Pool Configuration
        config_layout = QHBoxLayout()
        config_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        min_count_label = QLabel("Min Count:")
        min_count_label.setMaximumWidth(100)
        config_layout.addWidget(min_count_label)
        self.min_count = IgnoreScrollWheelSpinBox()
        self.min_count.setValue(self.pool.minCount)
        self.min_count.setMaximumWidth(100)
        config_layout.addWidget(self.min_count)
        config_layout.addSpacing(150)

        max_count_label = QLabel("Max Count:")
        max_count_label.setMaximumWidth(100)
        config_layout.addWidget(max_count_label)
        self.max_count = IgnoreScrollWheelSpinBox()
        self.pool.maxCount = 2147483647 if self.pool.maxCount > 2147483647 else self.pool.maxCount
        self.max_count.setValue(self.pool.maxCount)
        self.max_count.setMaximumWidth(100)
        config_layout.addWidget(self.max_count)
        config_layout.addSpacing(150)


        min_greater_label = QLabel("Min Greater Affixes:")
        min_greater_label.setMaximumWidth(100)
        config_layout.addWidget(min_greater_label)
        self.min_greater = IgnoreScrollWheelSpinBox()
        self.min_greater.setValue(self.pool.minGreaterAffixCount)
        self.min_greater.setMaximumWidth(100)
        config_layout.addWidget(self.min_greater)

        layout.addLayout(config_layout)

        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        affix_label = QLabel("Affixes")
        value_label = QLabel("Value")
        comparison_label = QLabel("Comparison")
        title_layout.addSpacing(250)
        title_layout.addWidget(affix_label)
        title_layout.addSpacing(400)
        title_layout.addWidget(value_label)
        title_layout.addSpacing(100)
        title_layout.addWidget(comparison_label)

        # Affix List
        self.affix_list = QListWidget()
        self.affix_list.setMinimumHeight(200)
        self.affix_list.setAlternatingRowColors(True)
        for affix in self.pool.count:
            self.add_affix_item(affix)

        affix_btn_layout = QHBoxLayout()
        add_affix_btn = QPushButton("Add Affix")
        add_affix_btn.clicked.connect(self.add_affix)
        affix_btn_layout.addWidget(add_affix_btn)
        remove_affix_btn = QPushButton("Remove Affix")
        remove_affix_btn.clicked.connect(lambda: self.remove_selected(self.affix_list))
        affix_btn_layout.addWidget(remove_affix_btn)

        layout.addLayout(affix_btn_layout)
        layout.addLayout(title_layout)
        layout.addWidget(self.affix_list)

        self.setLayout(layout)

    def add_affix_item(self, affix: AffixFilterModel):
        item = QListWidgetItem()
        widget = AffixWidget(affix)
        item.setSizeHint(widget.sizeHint())
        self.affix_list.addItem(item)
        self.affix_list.setItemWidget(item, widget)

    def add_affix(self):
        new_affix = AffixFilterModel(name=list(Dataloader().affix_dict.keys())[0], value=None)
        self.pool.count.append(new_affix)
        self.add_affix_item(new_affix)

    def remove_selected(self, list_widget):
        for item in list_widget.selectedItems():
            row = list_widget.row(item)
            list_widget.takeItem(row)
            del self.pool.count[row]

class AffixWidget(QWidget):
    def __init__(self, affix: AffixFilterModel, parent=None):
        super().__init__(parent)
        self.affix = affix
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Affix Name Combobox
        self.name_combo = IgnoreScrollWheelComboBox()
        self.name_combo.addItems(sorted(Dataloader().affix_dict.keys()))
        self.name_combo.setMaximumWidth(600)
        if self.affix.name in Dataloader().affix_dict:
            self.name_combo.setCurrentText(self.affix.name)
        self.name_combo.currentTextChanged.connect(self.update_name)

        # Value Input
        self.value_edit = QLineEdit()
        self.value_edit.setMaximumWidth(100)
        self.value_edit.setPlaceholderText("Value (optional)")
        if self.affix.value is not None:
            self.value_edit.setText(str(self.affix.value))
        self.value_edit.textChanged.connect(self.update_value)

        # Comparison Combobox
        self.comparison_combo = IgnoreScrollWheelComboBox()
        self.comparison_combo.setMaximumWidth(100)
        self.comparison_combo.addItems([ct.value for ct in ComparisonType])
        self.comparison_combo.setCurrentText(self.affix.comparison.value)
        self.comparison_combo.currentTextChanged.connect(self.update_comparison)

        layout.addWidget(self.name_combo)
        layout.addSpacing(50)
        layout.addWidget(self.value_edit)
        layout.addSpacing(50)
        layout.addWidget(self.comparison_combo)
        self.setLayout(layout)

    def update_name(self, name):
        self.affix.name = name

    def update_value(self, value):
        try:
            self.affix.value = float(value) if value else None
        except ValueError:
            pass

    def update_comparison(self, comparison):
        self.affix.comparison = ComparisonType(comparison)

class AffixesTab(QTabWidget):
    def __init__(self, profile_model: ProfileModel, parent=None):
        super().__init__(parent)
        self.profile_model = profile_model
        self.setup_ui()

    def setup_ui(self):
        """Populate the grid layout with existing groups"""
        for idx, affix_group in enumerate(self.profile_model.Affixes):
            for item_name, config in affix_group.root.items():
                group = AffixGroupEditor(item_name, ItemType(config.itemType[0]), config)
                self.addTab(group, item_name)

    def add_item_type(self):
        item_type, ok = QInputDialog.getItem(
            self, "Add Item Type", "Select:", [e.value for e in ItemType]
        )
        if ok and item_type:
            new_filter = ItemFilterModel(
                itemType=[ItemType(item_type)],
                minPower=0
            )
            dynamic_filter = DynamicItemFilterModel(root={item_type: new_filter})
            self.profile_model.Affixes.append(dynamic_filter)

            group = AffixGroupEditor(ItemType(item_type), new_filter)
            # self.addTab(group, )

    def save_all(self):
        # Save all group configurations
        for i in range(self.container_layout.count()):
            widget = self.container_layout.itemAt(i).widget()
            if isinstance(widget, AffixGroupEditor):
                widget.save_config()
