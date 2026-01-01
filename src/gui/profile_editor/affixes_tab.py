import logging

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.config.models import AffixFilterCountModel, AffixFilterModel, ComparisonType, DynamicItemFilterModel
from src.dataloader import Dataloader
from src.gui.collapsible_widget import Container
from src.gui.dialog import (
    CreateItem,
    DeleteAffixPool,
    DeleteItem,
    IgnoreScrollWheelComboBox,
    IgnoreScrollWheelSpinBox,
    MinGreaterDialog,
    MinPowerDialog,
)
from src.item.data.item_type import ItemType, is_armor, is_jewelry, is_weapon

LOGGER = logging.getLogger(__name__)

AFFIXES_TABNAME = "Affixes"


class AffixGroupEditor(QWidget):
    def __init__(self, dynamic_filter: DynamicItemFilterModel, parent=None):
        super().__init__(parent)
        for item_name, config in dynamic_filter.root.items():
            self.item_name = item_name
            self.config = config

        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
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
        self.item_type_combo.setEditable(True)
        self.item_type_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.item_type_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        item_types_names = [
            item.name for item in ItemType.__members__.values() if is_armor(item) or is_jewelry(item) or is_weapon(item)
        ]
        self.item_type_combo.addItems(item_types_names)
        self.item_type_combo.setCurrentText(self.config.itemType[0].name)
        self.item_type_combo.setMaximumWidth(150)
        self.item_type_combo.currentIndexChanged.connect(self.update_item_type)
        general_form.addRow("Item Type:", self.item_type_combo)
        self.min_power = IgnoreScrollWheelSpinBox()
        self.min_power.setMaximum(800)
        self.min_power.setValue(self.config.minPower)
        self.min_power.setMaximumWidth(150)
        self.min_power.valueChanged.connect(self.update_min_power)
        general_form.addRow("Minimum Power:", self.min_power)

        # Min Greater Affixes with auto-sync checkbox
        min_greater_layout = QHBoxLayout()

        self.min_greater = QSpinBox()  # Changed from IgnoreScrollWheelSpinBox()
        self.min_greater.setValue(self.config.minGreaterAffixCount)
        self.min_greater.setMaximum(4)
        self.min_greater.setMinimum(0)
        self.min_greater.setMaximumWidth(80)
        self.min_greater.setToolTip(
            "Minimum number of checked affixes that must be Greater Affixes.\n"
            "0 = Accept items even without GAs (for leveling)\n"
            "1-4 = At least this many checked affixes must be GA"
        )
        self.min_greater.valueChanged.connect(self.update_min_greater_affix)

        # Auto-sync checkbox
        self.auto_sync_checkbox = QCheckBox("Auto Sync")
        self.auto_sync_checkbox.setToolTip(
            "When checked: Min Greater Affixes automatically matches the number of affixes marked as 'want greater'\n"
            "When unchecked: You can manually set Min Greater Affixes to any value"
        )
        # Load saved auto-sync state from model
        self.auto_sync_checkbox.setChecked(getattr(self.config, "auto_sync_ga", False))
        self.auto_sync_checkbox.stateChanged.connect(self.toggle_auto_sync)

        # Apply initial styling if auto-sync is enabled
        if self.auto_sync_checkbox.isChecked():
            self.min_greater.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: #888888; }")

        # Helper text showing current checkbox count
        self.greater_count_label = QLabel()
        self.greater_count_label.setStyleSheet("color: gray; font-style: italic;")
        self.update_greater_count_label()

        min_greater_layout.addWidget(self.min_greater)
        min_greater_layout.addWidget(self.auto_sync_checkbox)
        min_greater_layout.addWidget(self.greater_count_label)
        min_greater_layout.addStretch()

        # Set initial enabled state based on auto-sync
        self.min_greater.setEnabled(not self.auto_sync_checkbox.isChecked())

        general_form.addRow("Min Greater Affixes:", min_greater_layout)

        self.content_layout.addLayout(general_form)

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

        # Affix Pool
        self.affix_pool_container = Container("Affix Pool")
        self.affix_pool_layout = QVBoxLayout(self.affix_pool_container.contentWidget)
        self.affix_pool_container.firstExpansion.connect(self.init_affix_pool)

        # Inherent Pool
        self.inherent_pool_container = Container("Inherent Pool")
        self.inherent_pool_layout = QVBoxLayout(self.inherent_pool_container.contentWidget)
        self.inherent_pool_container.firstExpansion.connect(self.init_inherent_pool)

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

        # Expand containers after a short delay to ensure everything is loaded
        QTimer.singleShot(100, self.affix_pool_container.expand)
        QTimer.singleShot(100, self.inherent_pool_container.expand)

    def init_affix_pool(self):
        """Initialize affix pool content on first expansion."""
        for pool in self.config.affixPool:
            self.add_affix_pool_item(pool)
        # Update count label after pools are loaded
        QTimer.singleShot(50, self.update_greater_count_label)

    def init_inherent_pool(self):
        """Initialize inherent pool content on first expansion."""
        for pool in self.config.inherentPool:
            self.add_affix_pool_item(pool, True)
        # Update count label after pools are loaded
        QTimer.singleShot(50, self.update_greater_count_label)

    def add_affix_pool_item(self, pool: AffixFilterCountModel, inherent: bool = False):
        if inherent:
            nb_count = self.inherent_pool_layout.count()
            container = Container(f"Count {nb_count}", True)
            container_layout = QVBoxLayout(container.contentWidget)
            widget = AffixPoolWidget(pool)
            container_layout.addWidget(widget)
            self.inherent_pool_layout.addWidget(container)
            QTimer.singleShot(50, container.expand)
        else:
            nb_count = self.affix_pool_layout.count()
            container = Container(f"Count {nb_count}", True)
            container_layout = QVBoxLayout(container.contentWidget)
            widget = AffixPoolWidget(pool)
            container_layout.addWidget(widget)
            self.affix_pool_layout.addWidget(container)
            QTimer.singleShot(50, container.expand)

    def add_affix_pool(self):
        # Create a default valid affix
        default_affix = AffixFilterModel(
            name=next(iter(Dataloader().affix_dict.keys())),  # First valid affix name
            value=None,
            comparison=ComparisonType.larger,
        )

        new_pool = AffixFilterCountModel(
            count=[default_affix],  # Start with at least one valid affix
            minCount=1,
            maxCount=3,
        )
        self.config.affixPool.append(new_pool)
        self.add_affix_pool_item(new_pool)

    def add_inherent_pool(self):
        # Create a default valid affix
        default_affix = AffixFilterModel(
            name=next(iter(Dataloader().affix_dict.keys())),  # First valid affix name
            value=None,
            comparison=ComparisonType.larger,
        )

        new_pool = AffixFilterCountModel(
            count=[default_affix],  # Start with at least one valid affix
            minCount=1,
            maxCount=3,
        )
        self.config.affixPool.append(new_pool)
        self.add_affix_pool_item(new_pool, True)

    def remove_selected(self, layout_widget: QVBoxLayout, inherent: bool = False):
        nb_pool = layout_widget.count()
        dialog = DeleteAffixPool(nb_pool, inherent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            to_delete = dialog.get_value()
            to_delete_list = []
            for i in range(layout_widget.count()):
                item = layout_widget.itemAt(i)
                if (
                    item and item.widget() is not None and item.widget().header.name in to_delete
                ):  # Check if the item is a widget
                    to_delete_list.append((item.widget(), i))
            to_delete_list.reverse()
            for widget, index in to_delete_list:
                widget.setParent(None)
                self.config.affixPool.pop(index)
            self.reorganize_pool(layout_widget)

    def reorganize_pool(self, layout_widget: QVBoxLayout):
        for i in range(layout_widget.count()):
            item = layout_widget.itemAt(i)
            if item and item.widget() is not None:  # Check if the item is a widget
                item.widget().header.set_name(f"Count {i}")

    def update_item_type(self):
        self.config.itemType = [ItemType(ItemType._member_map_[self.item_type_combo.currentText()])]

    def update_min_power(self):
        self.config.minPower = self.min_power.value()

    def update_min_greater_affix(self):
        self.config.minGreaterAffixCount = self.min_greater.value()

    def toggle_auto_sync(self):
        """Enable/disable auto-sync mode for min_greater spinner"""
        is_auto_sync = self.auto_sync_checkbox.isChecked()

        # Save state to model
        self.config.auto_sync_ga = is_auto_sync

        # Enable/disable the spinner
        self.min_greater.setEnabled(not is_auto_sync)

        if is_auto_sync:
            # Apply gray styling
            self.min_greater.setStyleSheet("QSpinBox { background-color: #3c3c3c; color: #888888; }")

            # Expand pools
            self.affix_pool_container.expand()
            self.inherent_pool_container.expand()

            # Count and update
            count = self.count_want_greater_affixes()
            self.min_greater.setValue(count)
            self.update_greater_count_label()
        else:
            self.min_greater.setStyleSheet("")

    def _update_auto_sync_count(self):
        """Helper to update count after pools are loaded"""
        count = self.count_want_greater_affixes()
        self.min_greater.setValue(count)
        self.update_greater_count_label()

    def sync_min_greater_from_checkboxes(self):
        """Update min_greater spinner to match checkbox count (only if auto-sync is enabled)"""
        if self.auto_sync_checkbox.isChecked():
            count = self.count_want_greater_affixes()
            self.min_greater.setValue(count)

    def count_want_greater_affixes(self):
        """Count how many affixes across all pools have want_greater checked"""
        want_greater_count = 0

        # Check if layouts exist yet
        if not hasattr(self, "affix_pool_layout") or not hasattr(self, "inherent_pool_layout"):
            return 0

        # Count checked boxes in affix pools
        for i in range(self.affix_pool_layout.count()):
            container = self.affix_pool_layout.itemAt(i).widget()
            if container and hasattr(container, "contentWidget"):
                pool_widget = container.contentWidget.layout().itemAt(0).widget()
                if isinstance(pool_widget, AffixPoolWidget):
                    for j in range(pool_widget.affix_list.count()):
                        list_item = pool_widget.affix_list.item(j)
                        affix_widget = pool_widget.affix_list.itemWidget(list_item)
                        if isinstance(affix_widget, AffixWidget) and affix_widget.greater_checkbox.isChecked():
                            want_greater_count += 1

        # Count checked boxes in inherent pools
        for i in range(self.inherent_pool_layout.count()):
            container = self.inherent_pool_layout.itemAt(i).widget()
            if container and hasattr(container, "contentWidget"):
                pool_widget = container.contentWidget.layout().itemAt(0).widget()
                if isinstance(pool_widget, AffixPoolWidget):
                    for j in range(pool_widget.affix_list.count()):
                        list_item = pool_widget.affix_list.item(j)
                        affix_widget = pool_widget.affix_list.itemWidget(list_item)
                        if isinstance(affix_widget, AffixWidget) and affix_widget.greater_checkbox.isChecked():
                            want_greater_count += 1

        return want_greater_count

    def update_greater_count_label(self):
        """Update the helper text showing how many affixes are marked as 'want greater'"""
        count = self.count_want_greater_affixes()
        if count == 0:
            self.greater_count_label.setText("(no greater affixes marked)")
        elif count == 1:
            self.greater_count_label.setText("(1 greater affix marked)")
        else:
            self.greater_count_label.setText(f"({count} greater affixes marked)")


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
        min_count_label.setStyleSheet("QLabel { color: #e0e0e0; }")  # ← ADD THIS
        config_layout.addWidget(min_count_label)
        self.min_count = IgnoreScrollWheelSpinBox()
        self.min_count.setValue(self.pool.minCount)
        self.min_count.setMaximumWidth(100)
        self.min_count.valueChanged.connect(self.update_min_count)
        config_layout.addWidget(self.min_count)
        config_layout.addSpacing(150)

        max_count_label = QLabel("Max Count:")
        max_count_label.setMaximumWidth(100)
        max_count_label.setStyleSheet("QLabel { color: #e0e0e0; }")  # ← ADD THIS
        config_layout.addWidget(max_count_label)
        self.max_count = IgnoreScrollWheelSpinBox()
        self.max_count.setValue(min(self.pool.maxCount, 2147483647))
        self.max_count.setMaximumWidth(100)
        self.max_count.valueChanged.connect(self.update_max_count)
        config_layout.addWidget(self.max_count)

        layout.addLayout(config_layout)

        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        affix_label = QLabel("Affixes")
        affix_label.setStyleSheet("QLabel { color: #e0e0e0; }")  # ← ADD THIS
        greater_label = QLabel("Greater")
        greater_label.setStyleSheet("QLabel { color: #e0e0e0; }")  # ← ADD THIS
        value_label = QLabel("Value")
        value_label.setStyleSheet("QLabel { color: #e0e0e0; }")  # ← ADD THIS
        comparison_label = QLabel("Comparison")
        comparison_label.setStyleSheet("QLabel { color: #e0e0e0; }")  # ← ADD THIS
        title_layout.addSpacing(250)
        title_layout.addWidget(affix_label)
        title_layout.addSpacing(400)
        title_layout.addWidget(greater_label)
        title_layout.addSpacing(95)
        title_layout.addWidget(value_label)
        title_layout.addSpacing(95)
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
        new_affix = AffixFilterModel(
            name=next(iter(Dataloader().affix_dict.keys())), value=None, comparison=ComparisonType.larger
        )
        self.pool.count.append(new_affix)
        self.add_affix_item(new_affix)

    def remove_selected(self, list_widget: QListWidget):
        for item in list_widget.selectedItems():
            row = list_widget.row(item)
            list_widget.takeItem(row)
            del self.pool.count[row]

    def update_min_count(self):
        self.pool.minCount = self.min_count.value()

    def update_max_count(self):
        self.pool.maxCount = self.max_count.value()


class AffixWidget(QWidget):
    def __init__(self, affix: AffixFilterModel, parent=None):
        super().__init__(parent)
        self.affix = affix
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.setSpacing(50)
        self.create_affix_name_combobox()
        self.create_greater_checkbox()
        self.create_value_input()
        self.create_comparison_combobox()
        layout.addWidget(self.name_combo)
        layout.addWidget(self.greater_checkbox)
        layout.addWidget(self.value_edit)
        layout.addWidget(self.comparison_combo)
        self.setLayout(layout)

    def create_affix_name_combobox(self):
        # Affix Name Combobox
        self.name_combo = IgnoreScrollWheelComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.name_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.name_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.name_combo.addItems(sorted(Dataloader().affix_dict.values()))
        self.name_combo.setMaximumWidth(600)
        if self.affix.name in Dataloader().affix_dict:
            self.name_combo.setCurrentText(Dataloader().affix_dict[self.affix.name])
        self.name_combo.currentIndexChanged.connect(self.update_name)

    def create_greater_checkbox(self):
        # Greater Affix Checkbox
        self.greater_checkbox = QCheckBox("Greater")
        self.greater_checkbox.setChecked(getattr(self.affix, "want_greater", False))
        self.greater_checkbox.setFixedWidth(80)
        self.greater_checkbox.setStyleSheet("QCheckBox { background-color: transparent; }")
        self.greater_checkbox.stateChanged.connect(self.update_greater)
        self.greater_checkbox.stateChanged.connect(self.update_parent_count_label)

    def update_parent_count_label(self):
        """Notify parent AffixGroupEditor to update its count label and sync if enabled"""
        parent = self.parent()
        while parent:
            if isinstance(parent, AffixGroupEditor):
                parent.update_greater_count_label()
                parent.sync_min_greater_from_checkboxes()  # Also trigger sync if enabled
                break
            parent = parent.parent()

    def create_value_input(self):
        # Value Input
        self.value_edit = QLineEdit()
        self.value_edit.setFixedSize(100, self.value_edit.sizeHint().height())
        self.value_edit.setPlaceholderText("Value (optional)")
        if self.affix.value is not None:
            self.value_edit.setText(str(self.affix.value))
        self.value_edit.textChanged.connect(self.update_value)
        self.affix.value = self.affix.value

    def create_comparison_combobox(self):
        # Comparison Combobox
        self.comparison_combo = IgnoreScrollWheelComboBox()
        self.comparison_combo.setEditable(True)
        self.comparison_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.comparison_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.comparison_combo.setFixedSize(100, self.comparison_combo.sizeHint().height())
        self.comparison_combo.addItems([ct.value for ct in ComparisonType])
        self.comparison_combo.setCurrentText(self.affix.comparison.value)
        self.comparison_combo.currentIndexChanged.connect(self.update_comparison)
        self.affix.comparison = ComparisonType(self.affix.comparison.value)

    def update_name(self):
        reverse_dict = {v: k for k, v in Dataloader().affix_dict.items()}
        self.affix.name = reverse_dict.get(self.name_combo.currentText())

    def update_value(self, value):
        try:
            self.affix.value = float(value) if value else None
        except ValueError:
            return

    def update_comparison(self):
        comparison = self.comparison_combo.currentText()
        self.affix.comparison = ComparisonType(comparison)

    def update_greater(self):
        self.affix.want_greater = self.greater_checkbox.isChecked()


class AffixesTab(QWidget):
    def __init__(self, affixes_model: list[DynamicItemFilterModel], parent=None):
        super().__init__(parent)
        self.affixes_model = affixes_model
        self.loaded = False

    def load(self):
        if not self.loaded:
            self.setup_ui()
            self.loaded = True

    def setup_ui(self):
        """Populate the grid layout with existing groups."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 20, 0, 20)
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.toolbar = QToolBar("MyToolBar", self)
        self.toolbar.setMinimumHeight(50)
        self.toolbar.setContentsMargins(10, 10, 10, 10)
        self.toolbar.setMovable(False)
        self.item_names = []
        for affix_group in self.affixes_model:
            for item_name in affix_group.root:
                if item_name in self.item_names:
                    QMessageBox.warning(
                        self, "Warning", f"Item name already exist please rename {item_name} in the profile file."
                    )
                    continue
                group = AffixGroupEditor(affix_group)
                self.item_names.append(item_name)
                self.tab_widget.addTab(group, item_name)
        # Add buttons to toolbar
        add_item_button = QPushButton()
        add_item_button.setText("Create Item")
        add_item_button.clicked.connect(self.add_item_type)
        remove_item_button = QPushButton()
        remove_item_button.setText("Remove Item")
        remove_item_button.clicked.connect(self.remove_item_type)
        set_all_minGreaterAffix_button = QPushButton("Set All Min GA's (Excludes Auto Synced Items)")
        set_all_minPower_button = QPushButton("Set all minPower")
        set_all_minGreaterAffix_button.clicked.connect(self.set_all_minGreaterAffix)
        set_all_minPower_button.clicked.connect(self.set_all_minPower)
        self.toolbar.addWidget(add_item_button)
        self.toolbar.addWidget(remove_item_button)
        self.toolbar.addWidget(set_all_minGreaterAffix_button)
        self.toolbar.addWidget(set_all_minPower_button)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addWidget(self.tab_widget)

    def show_message(self, text):
        QMessageBox.information(self, "Info", text)

    def add_item_type(self):
        dialog = CreateItem(self.item_names, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item = dialog.get_value()
            for item_name in item.root:
                group = AffixGroupEditor(item)
                self.item_names.append(item_name)
                self.tab_widget.addTab(group, item_name)
                self.affixes_model.append(item)
            return

    def close_tab(self, index):
        self.item_names.pop(index)
        self.tab_widget.removeTab(index)
        self.affixes_model.pop(index)

    def remove_item_type(self):
        dialog = DeleteItem(self.item_names, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item_names_to_delete = dialog.get_value()
            for item_name in item_names_to_delete:
                index = self.item_names.index(item_name)
                self.item_names.remove(item_name)
                self.tab_widget.removeTab(index)
                self.affixes_model.pop(index)
            return

    def set_all_minGreaterAffix(self):
        dialog = MinGreaterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            minGreaterAffix = dialog.get_value()
            for i in range(self.tab_widget.count()):
                tab: AffixGroupEditor = self.tab_widget.widget(i)
                # Skip if auto-sync is enabled
                if tab.auto_sync_checkbox.isChecked():
                    continue
                tab.min_greater.setValue(minGreaterAffix)
                tab.update_min_greater_affix()

    def set_all_minPower(self):
        dialog = MinPowerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            minPower = dialog.get_value()
            for i in range(self.tab_widget.count()):
                tab: AffixGroupEditor = self.tab_widget.widget(i)
                tab.min_power.setValue(minPower)
                tab.update_min_power()