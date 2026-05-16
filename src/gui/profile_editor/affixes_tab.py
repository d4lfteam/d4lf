import logging

from PyQt6.QtCore import QEvent, QSettings, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QDoubleValidator, QIntValidator
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
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

from src.config.profile_models import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    DynamicItemFilterModel,
)
from src.dataloader import Dataloader
from src.gui.collapsible_widget import Container
from src.gui.dialog import (
    CreateItem,
    DeleteAffixPool,
    DeleteItem,
    IgnoreScrollWheelComboBox,
    IgnoreScrollWheelSpinBox,
    MinGreaterDialog,
    MinPercentDialog,
    MinPowerDialog,
)
from src.item.data.item_type import ItemType, is_armor, is_jewelry, is_weapon

LOGGER = logging.getLogger(__name__)

AFFIXES_TABNAME = "Affixes"
AFFIX_VALUE_MODE = "Value"
AFFIX_PERCENT_MODE = "Min %"


class CheckableComboBox(IgnoreScrollWheelComboBox):
    checked_items_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.lineEdit().setReadOnly(True)
        self.view().viewport().installEventFilter(self)

    def add_checkable_item(self, text: str, checked: bool):
        self.addItem(text)
        index = self.count() - 1
        item = self.model().item(index, self.modelColumn())
        if item is not None:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        check_state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.setItemData(index, check_state, Qt.ItemDataRole.CheckStateRole)
        self.refresh_text()

    def checked_item_texts(self):
        return [
            self.itemText(i)
            for i in range(self.count())
            if self.itemData(i, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked
        ]

    def set_all_checked(self):
        self.blockSignals(True)
        for i in range(self.count()):
            self.setItemData(i, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
        self.blockSignals(False)
        self.refresh_text()
        self.checked_items_changed.emit()

    def set_all_unchecked(self):
        self.blockSignals(True)
        for i in range(self.count()):
            self.setItemData(i, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.blockSignals(False)
        self.refresh_text()
        self.checked_items_changed.emit()

    def toggle_item(self, index: int):
        check_state = self.itemData(index, Qt.ItemDataRole.CheckStateRole)
        new_state = Qt.CheckState.Unchecked if check_state == Qt.CheckState.Checked else Qt.CheckState.Checked
        self.setItemData(index, new_state, Qt.ItemDataRole.CheckStateRole)
        self.refresh_text()
        self.checked_items_changed.emit()

    def refresh_text(self):
        checked_items = self.checked_item_texts()
        if len(checked_items) == self.count():
            text = "All"
        elif not checked_items:
            text = "None"
        elif len(checked_items) <= 2:
            text = ", ".join(checked_items)
        else:
            text = f"{len(checked_items)} selected"
        self.lineEdit().setText(text)

    def eventFilter(self, watched, event):
        if watched == self.view().viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            index = self.view().indexAt(event.position().toPoint())
            if index.isValid():
                self.toggle_item(index.row())
                return True
        return super().eventFilter(watched, event)


class AffixGroupEditor(QWidget):
    def __init__(self, dynamic_filter: DynamicItemFilterModel, parent=None):
        super().__init__(parent)
        self.settings = QSettings("d4lf", "profile_editor")
        for item_name, config in dynamic_filter.root.items():
            self.item_name = item_name
            self.config = config

        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.setup_ui()

    def setup_ui(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        general_form = QFormLayout()

        self.item_types = [
            item for item in ItemType.__members__.values() if is_armor(item) or is_jewelry(item) or is_weapon(item)
        ]
        selected_item_types = self.config.itemType or self.item_types
        self.item_type_combo = CheckableComboBox()
        self.item_type_combo.setMaximumWidth(180)
        for item_type in self.item_types:
            self.item_type_combo.add_checkable_item(item_type.name, item_type in selected_item_types)
        self.item_type_combo.checked_items_changed.connect(self.update_item_types)

        item_type_layout = QHBoxLayout()
        item_type_layout.addWidget(self.item_type_combo)
        all_item_types_btn = QPushButton("All")
        all_item_types_btn.setMaximumWidth(50)
        all_item_types_btn.clicked.connect(self.select_all_item_types)
        reset_item_types_btn = QPushButton("Reset")
        reset_item_types_btn.setMaximumWidth(60)
        reset_item_types_btn.clicked.connect(self.reset_item_types)
        item_type_layout.addWidget(all_item_types_btn)
        item_type_layout.addWidget(reset_item_types_btn)
        item_type_layout.addStretch()
        general_form.addRow("Item Types:", item_type_layout)

        self.min_power = IgnoreScrollWheelSpinBox()
        self.min_power.setMaximum(800)
        self.min_power.setValue(self.config.minPower)
        self.min_power.setMaximumWidth(150)
        self.min_power.valueChanged.connect(self.update_min_power)
        general_form.addRow("Minimum Power:", self.min_power)

        min_greater_layout = QHBoxLayout()

        self.min_greater = QSpinBox()
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

        self.auto_sync_checkbox = QCheckBox("Auto Sync")
        self.auto_sync_checkbox.setToolTip(
            "When checked: Min Greater Affixes automatically matches the number of affixes marked as 'want greater'\n"
            "When unchecked: You can manually set Min Greater Affixes to any value"
        )
        self.auto_sync_checkbox.setChecked(self.settings.value(f"auto_sync_ga_{self.item_name}", False, type=bool))
        self.auto_sync_checkbox.stateChanged.connect(self.toggle_auto_sync)

        self.greater_count_label = QLabel()
        self.greater_count_label.setProperty("greaterCountLabel", True)
        self._refresh_widget_style(self.greater_count_label)
        self.update_greater_count_label()

        min_greater_layout.addWidget(self.min_greater)
        min_greater_layout.addWidget(self.auto_sync_checkbox)
        min_greater_layout.addWidget(self.greater_count_label)
        min_greater_layout.addStretch()

        self.min_greater.setEnabled(not self.auto_sync_checkbox.isChecked())

        if self.auto_sync_checkbox.isChecked():
            self.min_greater.setProperty("autoSyncSpin", True)
            self._refresh_widget_style(self.min_greater)

        general_form.addRow("Min Greater Affixes:", min_greater_layout)

        self.content_layout.addLayout(general_form)
        self.create_unique_aspect_groupbox()

        pool_btn_layout = QHBoxLayout()
        add_affix_pool_btn = QPushButton("Add Affix Pool")
        add_affix_pool_btn.clicked.connect(self.add_affix_pool)
        add_inherent_pool_btn = QPushButton("Add Inherent Pool")
        add_inherent_pool_btn.clicked.connect(self.add_inherent_pool)
        remove_affix_pool_btn = QPushButton("Remove Affix Pool")
        remove_affix_pool_btn.clicked.connect(lambda: self.remove_selected(self.affix_pool_layout))
        remove_inherent_pool_btn = QPushButton("Remove Inherent Pool")
        remove_inherent_pool_btn.clicked.connect(lambda: self.remove_selected(self.inherent_pool_layout, inherent=True))

        pool_btn_layout.addWidget(add_affix_pool_btn)
        pool_btn_layout.addWidget(add_inherent_pool_btn)
        pool_btn_layout.addWidget(remove_affix_pool_btn)
        pool_btn_layout.addWidget(remove_inherent_pool_btn)

        self.affix_pool_container = Container("Affix Pool")
        self.affix_pool_layout = QVBoxLayout(self.affix_pool_container.contentWidget)
        self.affix_pool_container.firstExpansion.connect(self.init_affix_pool)

        self.inherent_pool_container = Container("Inherent Pool")
        self.inherent_pool_layout = QVBoxLayout(self.inherent_pool_container.contentWidget)
        self.inherent_pool_container.firstExpansion.connect(self.init_inherent_pool)

        self.content_layout.addWidget(self.affix_pool_container)
        self.content_layout.addWidget(self.inherent_pool_container)
        self.content_layout.addLayout(pool_btn_layout)

        scroll_area.setWidget(content_widget)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

        QTimer.singleShot(100, self.affix_pool_container.expand)
        QTimer.singleShot(100, self.inherent_pool_container.expand)

    def create_unique_aspect_groupbox(self):
        self.unique_aspect_groupbox = QGroupBox("Unique Aspect")
        self.unique_aspect_form = QFormLayout()

        self.unique_aspect_name_combo = IgnoreScrollWheelComboBox()
        self.unique_aspect_name_combo.setEditable(True)
        self.unique_aspect_name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.unique_aspect_name_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.unique_aspect_name_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.unique_aspect_name_combo.addItems(sorted(Dataloader().aspect_unique_dict.keys()))
        if self.config.uniqueAspect is not None:
            self.unique_aspect_name_combo.setCurrentText(self.config.uniqueAspect.name)
        else:
            self.unique_aspect_name_combo.setCurrentText("")
        self.unique_aspect_name_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.unique_aspect_name_combo.setMinimumContentsLength(24)
        self.unique_aspect_name_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.unique_aspect_name_combo.setMaximumWidth(600)
        self.unique_aspect_name_combo.currentTextChanged.connect(self.update_unique_aspect_name)
        self.unique_aspect_form.addRow("Name:", self.unique_aspect_name_combo)

        self.unique_aspect_mode_combo = IgnoreScrollWheelComboBox()
        self.unique_aspect_mode_combo.setFixedSize(100, self.unique_aspect_mode_combo.sizeHint().height())
        self.unique_aspect_mode_combo.addItems([AFFIX_VALUE_MODE, AFFIX_PERCENT_MODE])
        if self.config.uniqueAspect is not None and self.config.uniqueAspect.minPercentOfAspect:
            self.unique_aspect_mode_combo.setCurrentText(AFFIX_PERCENT_MODE)
        else:
            self.unique_aspect_mode_combo.setCurrentText(AFFIX_VALUE_MODE)
        self.unique_aspect_mode_combo.currentTextChanged.connect(self.update_unique_aspect_mode)
        self.unique_aspect_form.addRow("Mode:", self.unique_aspect_mode_combo)

        self.unique_aspect_value_edit = QLineEdit()
        self.unique_aspect_value_edit.setFixedSize(100, self.unique_aspect_value_edit.sizeHint().height())
        self.unique_aspect_value_edit.textChanged.connect(self.update_unique_aspect_value)
        self.unique_aspect_form.addRow("Threshold:", self.unique_aspect_value_edit)

        self.unique_aspect_groupbox.setLayout(self.unique_aspect_form)
        self.content_layout.addWidget(self.unique_aspect_groupbox)
        self.refresh_unique_aspect_value_input()
        self.set_unique_aspect_controls_enabled()

    def _refresh_widget_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def set_unique_aspect_controls_enabled(self):
        enabled = self.config.uniqueAspect is not None
        self.unique_aspect_name_combo.setEnabled(True)
        self.unique_aspect_mode_combo.setEnabled(enabled)
        self.unique_aspect_value_edit.setEnabled(enabled)

    def update_unique_aspect_name(self, current_text=None):
        aspect_name = self.unique_aspect_name_combo.currentText() if current_text is None else current_text
        aspect_name = aspect_name.strip()
        if not aspect_name:
            self.config.uniqueAspect = None
            self.refresh_unique_aspect_value_input()
            self.set_unique_aspect_controls_enabled()
            return
        if aspect_name not in Dataloader().aspect_unique_dict:
            return
        if self.config.uniqueAspect is None:
            self.config.uniqueAspect = AspectUniqueFilterModel(name=aspect_name)
        else:
            self.config.uniqueAspect.name = aspect_name
        self.refresh_unique_aspect_value_input()
        self.set_unique_aspect_controls_enabled()

    def refresh_unique_aspect_value_input(self):
        self.unique_aspect_value_edit.blockSignals(True)
        if self.config.uniqueAspect is None:
            self.unique_aspect_value_edit.setText("")
            self.unique_aspect_value_edit.setPlaceholderText("Value (optional)")
            self.unique_aspect_value_edit.setValidator(QDoubleValidator(self.unique_aspect_value_edit))
        elif self.unique_aspect_mode_combo.currentText() == AFFIX_PERCENT_MODE:
            self.unique_aspect_value_edit.setPlaceholderText("Percent (0-100)")
            self.unique_aspect_value_edit.setValidator(QIntValidator(0, 100, self.unique_aspect_value_edit))
            display_value = (
                ""
                if self.config.uniqueAspect.minPercentOfAspect == 0
                else str(self.config.uniqueAspect.minPercentOfAspect)
            )
            self.unique_aspect_value_edit.setText(display_value)
        else:
            self.unique_aspect_value_edit.setPlaceholderText("Value (optional)")
            self.unique_aspect_value_edit.setValidator(QDoubleValidator(self.unique_aspect_value_edit))
            display_value = "" if self.config.uniqueAspect.value is None else str(self.config.uniqueAspect.value)
            self.unique_aspect_value_edit.setText(display_value)
        self.unique_aspect_value_edit.blockSignals(False)

    def update_unique_aspect_mode(self, current_text=None):
        if self.config.uniqueAspect is None:
            self.set_unique_aspect_controls_enabled()
            return
        mode = current_text or self.unique_aspect_mode_combo.currentText()
        if mode == AFFIX_PERCENT_MODE:
            self.config.uniqueAspect.value = None
        else:
            self.config.uniqueAspect.minPercentOfAspect = 0
        self.refresh_unique_aspect_value_input()
        self.set_unique_aspect_controls_enabled()

    def update_unique_aspect_value(self, value):
        if self.config.uniqueAspect is None:
            return
        if self.unique_aspect_mode_combo.currentText() == AFFIX_PERCENT_MODE:
            try:
                percent = int(value) if value else 0
            except ValueError:
                return
            if not 0 <= percent <= 100:
                QMessageBox.warning(self, "Warning", "Min % must be between 0 and 100.")
                self.refresh_unique_aspect_value_input()
                return
            self.config.uniqueAspect.minPercentOfAspect = percent
            self.config.uniqueAspect.value = None
            return

        try:
            self.config.uniqueAspect.value = float(value) if value else None
        except ValueError:
            return
        self.config.uniqueAspect.minPercentOfAspect = 0

    def init_affix_pool(self):
        """Initialize affix pool content on first expansion."""
        for pool in self.config.affixPool:
            self.add_affix_pool_item(pool)
        QTimer.singleShot(50, self.update_greater_count_label)

    def init_inherent_pool(self):
        """Initialize inherent pool content on first expansion."""
        for pool in self.config.inherentPool:
            self.add_affix_pool_item(pool, True)
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
        default_affix = AffixFilterModel(
            name=next(iter(Dataloader().affix_dict.keys())),  # First valid affix name
            value=None,
        )

        new_pool = AffixFilterCountModel(count=[default_affix], minCount=1, maxCount=3)
        self.config.affixPool.append(new_pool)
        self.add_affix_pool_item(new_pool)

    def add_inherent_pool(self):
        default_affix = AffixFilterModel(
            name=next(iter(Dataloader().affix_dict.keys())),  # First valid affix name
            value=None,
        )

        new_pool = AffixFilterCountModel(count=[default_affix], minCount=1, maxCount=3)
        self.config.inherentPool.append(new_pool)
        self.add_affix_pool_item(new_pool, True)

    def remove_selected(self, layout_widget: QVBoxLayout, inherent: bool = False):
        nb_pool = layout_widget.count()
        dialog = DeleteAffixPool(nb_pool, inherent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            to_delete = dialog.get_value()
            to_delete_list = []
            for i in range(layout_widget.count()):
                item = layout_widget.itemAt(i)
                if item and item.widget() is not None and item.widget().header.name in to_delete:
                    to_delete_list.append((item.widget(), i))
            to_delete_list.reverse()
            for widget, index in to_delete_list:
                widget.setParent(None)
                if inherent:
                    self.config.inherentPool.pop(index)
                else:
                    self.config.affixPool.pop(index)
            self.reorganize_pool(layout_widget)

    def reorganize_pool(self, layout_widget: QVBoxLayout):
        for i in range(layout_widget.count()):
            item = layout_widget.itemAt(i)
            if item and item.widget() is not None:
                item.widget().header.set_name(f"Count {i}")

    def update_item_types(self):
        self.config.itemType = [
            ItemType[item_name]
            for item_name in self.item_type_combo.checked_item_texts()
            if item_name in ItemType.__members__
        ]

    def select_all_item_types(self):
        self.item_type_combo.set_all_checked()

    def reset_item_types(self):
        self.item_type_combo.set_all_unchecked()

    def update_min_power(self):
        self.config.minPower = self.min_power.value()

    def update_min_greater_affix(self):
        self.config.minGreaterAffixCount = self.min_greater.value()

    def toggle_auto_sync(self):
        is_auto_sync = self.auto_sync_checkbox.isChecked()

        # Save UI-only state (replaces writing to config)
        self.settings.setValue(f"auto_sync_ga_{self.item_name}", is_auto_sync)

        # Keep your existing behavior
        self.min_greater.setEnabled(not is_auto_sync)

        if is_auto_sync:
            self.min_greater.setProperty("autoSyncSpin", True)
            self._refresh_widget_style(self.min_greater)

            self.affix_pool_container.expand()
            self.inherent_pool_container.expand()

            count = self.count_want_greater_affixes()
            self.min_greater.setValue(count)
            self.update_greater_count_label()
        else:
            self.min_greater.setProperty("autoSyncSpin", False)
            self._refresh_widget_style(self.min_greater)

    def _update_auto_sync_count(self):
        count = self.count_want_greater_affixes()
        self.min_greater.setValue(count)
        self.update_greater_count_label()

    def sync_min_greater_from_checkboxes(self):
        if self.auto_sync_checkbox.isChecked():
            count = self.count_want_greater_affixes()
            self.min_greater.setValue(count)

    def _ensure_pool_widgets_initialized(self):
        for container in (self.affix_pool_container, self.inherent_pool_container):
            was_visible = container.contentWidget.isVisible()
            if container.header.first_expansion:
                container.expand()
                if not was_visible:
                    container.collapse()

    def iter_affix_widgets(self):
        self._ensure_pool_widgets_initialized()

        # Inherents do not participate in Greater Affix auto-sync or bulk Min % updates.
        for i in range(self.affix_pool_layout.count()):
            container = self.affix_pool_layout.itemAt(i).widget()
            if container is None or not hasattr(container, "contentWidget"):
                continue
            pool_item = container.contentWidget.layout().itemAt(0)
            if pool_item is None:
                continue
            pool_widget = pool_item.widget()
            if not isinstance(pool_widget, AffixPoolWidget):
                continue
            for j in range(pool_widget.affix_list.count()):
                list_item = pool_widget.affix_list.item(j)
                affix_widget = pool_widget.affix_list.itemWidget(list_item)
                if isinstance(affix_widget, AffixWidget):
                    yield affix_widget

    def count_want_greater_affixes(self):
        want_greater_count = 0

        if not hasattr(self, "affix_pool_layout") or not hasattr(self, "inherent_pool_layout"):
            return 0

        for affix_widget in self.iter_affix_widgets():
            if affix_widget.greater_checkbox.isChecked():
                want_greater_count += 1

        return want_greater_count

    def update_greater_count_label(self):
        count = self.count_want_greater_affixes()
        if count == 0:
            self.greater_count_label.setText("(no greater affixes marked)")
        elif count == 1:
            self.greater_count_label.setText("(1 greater affix marked)")
        else:
            self.greater_count_label.setText(f"({count} greater affixes marked)")

    def convert_all_to_min_percent_of_affix(self, percent: int):
        for affix_widget in self.iter_affix_widgets():
            affix_widget.set_min_percent(percent, convert_mode=True)


class AffixPoolWidget(QWidget):
    def __init__(self, pool: AffixFilterCountModel, parent=None):
        super().__init__(parent)
        self.pool = pool
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        config_layout = QHBoxLayout()
        config_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        min_count_label = QLabel("Min Count:")
        min_count_label.setMaximumWidth(100)
        min_count_label.setProperty("affixHeaderLabel", True)
        self._refresh_widget_style(min_count_label)
        config_layout.addWidget(min_count_label)

        self.min_count = IgnoreScrollWheelSpinBox()
        self.min_count.setValue(self.pool.minCount)
        self.min_count.setMaximumWidth(100)
        self.min_count.valueChanged.connect(self.update_min_count)
        config_layout.addWidget(self.min_count)
        config_layout.addSpacing(150)

        max_count_label = QLabel("Max Count:")
        max_count_label.setMaximumWidth(100)
        max_count_label.setProperty("affixHeaderLabel", True)
        self._refresh_widget_style(max_count_label)
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
        affix_label.setProperty("affixHeaderLabel", True)
        self._refresh_widget_style(affix_label)

        greater_label = QLabel("Greater")
        greater_label.setProperty("affixHeaderLabel", True)
        self._refresh_widget_style(greater_label)

        mode_label = QLabel("Mode")
        mode_label.setProperty("affixHeaderLabel", True)
        self._refresh_widget_style(mode_label)

        value_label = QLabel("Threshold")
        value_label.setProperty("affixHeaderLabel", True)
        self._refresh_widget_style(value_label)

        title_layout.addSpacing(250)
        title_layout.addWidget(affix_label)
        title_layout.addSpacing(400)
        title_layout.addWidget(greater_label)
        title_layout.addSpacing(70)
        title_layout.addWidget(mode_label)
        title_layout.addSpacing(85)
        title_layout.addWidget(value_label)

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

    def _refresh_widget_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def add_affix_item(self, affix: AffixFilterModel):
        item = QListWidgetItem()
        widget = AffixWidget(affix)
        item.setSizeHint(widget.sizeHint())
        self.affix_list.addItem(item)
        self.affix_list.setItemWidget(item, widget)

    def add_affix(self):
        new_affix = AffixFilterModel(name=next(iter(Dataloader().affix_dict.keys())), value=None)
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
        self.create_mode_combobox()
        self.create_value_input()
        self.mode_combo.currentTextChanged.connect(self.update_mode)
        self.update_mode(self.mode_combo.currentText())

        layout.addWidget(self.name_combo)
        layout.addWidget(self.greater_checkbox)
        layout.addWidget(self.mode_combo)
        layout.addWidget(self.value_edit)

        self.setLayout(layout)

    def create_affix_name_combobox(self):
        self.name_combo = IgnoreScrollWheelComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.name_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.name_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.name_combo.addItems(sorted(Dataloader().affix_dict.values()))
        self.name_combo.setMaximumWidth(600)
        if self.affix.name in Dataloader().affix_dict:
            self.name_combo.setCurrentText(Dataloader().affix_dict[self.affix.name])
        # currentIndexChanged misses some editable-combobox keyboard flows.
        self.name_combo.currentTextChanged.connect(self.update_name)

    def create_greater_checkbox(self):
        self.greater_checkbox = QCheckBox("Greater")
        self.greater_checkbox.setChecked(getattr(self.affix, "want_greater", False))
        self.greater_checkbox.setFixedWidth(80)
        self.greater_checkbox.setProperty("greaterCheckbox", True)
        self._refresh_widget_style(self.greater_checkbox)
        self.greater_checkbox.stateChanged.connect(self.update_greater)
        self.greater_checkbox.stateChanged.connect(self.update_parent_count_label)

    def _refresh_widget_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def update_parent_count_label(self):
        parent = self.parent()
        while parent:
            if isinstance(parent, AffixGroupEditor):
                parent.update_greater_count_label()
                parent.sync_min_greater_from_checkboxes()
                break
            parent = parent.parent()

    def create_mode_combobox(self):
        self.mode_combo = IgnoreScrollWheelComboBox()
        self.mode_combo.setFixedSize(100, self.mode_combo.sizeHint().height())
        self.mode_combo.addItems([AFFIX_VALUE_MODE, AFFIX_PERCENT_MODE])
        if self.affix.minPercentOfAffix:
            self.mode_combo.setCurrentText(AFFIX_PERCENT_MODE)
        else:
            self.mode_combo.setCurrentText(AFFIX_VALUE_MODE)

    def create_value_input(self):
        self.value_edit = QLineEdit()
        self.value_edit.setFixedSize(100, self.value_edit.sizeHint().height())
        self.value_edit.textChanged.connect(self.update_value)

    def update_name(self, current_text=None):
        """Update the model only when the editable combobox contains a valid affix."""
        reverse_dict = {v: k for k, v in Dataloader().affix_dict.items()}
        affix_name = reverse_dict.get(current_text or self.name_combo.currentText())
        if affix_name is None:
            return
        self.affix.name = affix_name

    def refresh_value_input(self):
        if self.mode_combo.currentText() == AFFIX_PERCENT_MODE:
            self.value_edit.setPlaceholderText("Percent (0-100)")
            self.value_edit.setValidator(QIntValidator(0, 100, self.value_edit))
            display_value = "" if self.affix.minPercentOfAffix == 0 else str(self.affix.minPercentOfAffix)
        else:
            self.value_edit.setPlaceholderText("Value (optional)")
            self.value_edit.setValidator(QDoubleValidator(self.value_edit))
            display_value = "" if self.affix.value is None else str(self.affix.value)

        self.value_edit.blockSignals(True)
        self.value_edit.setText(display_value)
        self.value_edit.blockSignals(False)

    def update_mode(self, current_text=None):
        mode = current_text or self.mode_combo.currentText()
        if mode == AFFIX_PERCENT_MODE:
            self.affix.value = None
        else:
            self.affix.minPercentOfAffix = 0
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
            self.affix.minPercentOfAffix = percent
            self.affix.value = None
            return

        try:
            self.affix.value = float(value) if value else None
        except ValueError:
            return
        self.affix.minPercentOfAffix = 0

    def update_greater(self):
        self.affix.want_greater = self.greater_checkbox.isChecked()

    def set_min_percent(self, percent: int, convert_mode: bool = False):
        if convert_mode and self.mode_combo.currentText() != AFFIX_PERCENT_MODE:
            self.mode_combo.setCurrentText(AFFIX_PERCENT_MODE)
        if self.mode_combo.currentText() != AFFIX_PERCENT_MODE:
            return
        self.value_edit.setText(str(percent))


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

        add_item_button = QPushButton()
        add_item_button.setText("Create Item")
        add_item_button.clicked.connect(self.add_item_type)

        remove_item_button = QPushButton()
        remove_item_button.setText("Remove Item")
        remove_item_button.clicked.connect(self.remove_item_type)

        set_all_minGreaterAffix_button = QPushButton("Set All Min GAs (Excludes Auto Synced Items)")
        convert_all_to_min_percent_button = QPushButton("Convert All To Min %")
        set_all_minPower_button = QPushButton("Set all minPower")
        set_all_minGreaterAffix_button.clicked.connect(self.set_all_minGreaterAffix)
        convert_all_to_min_percent_button.clicked.connect(self.convert_all_to_min_percent_of_affix)
        set_all_minPower_button.clicked.connect(self.set_all_minPower)

        self.toolbar.addWidget(add_item_button)
        self.toolbar.addWidget(remove_item_button)
        self.toolbar.addWidget(set_all_minGreaterAffix_button)
        self.toolbar.addWidget(convert_all_to_min_percent_button)
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
                if tab.auto_sync_checkbox.isChecked():
                    continue
                tab.min_greater.setValue(minGreaterAffix)
                tab.update_min_greater_affix()

    def convert_all_to_min_percent_of_affix(self):
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, AffixGroupEditor):
            dialog = MinPercentDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                current_tab.convert_all_to_min_percent_of_affix(dialog.get_value())

    def set_all_minPower(self):
        dialog = MinPowerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            minPower = dialog.get_value()
            for i in range(self.tab_widget.count()):
                tab: AffixGroupEditor = self.tab_widget.widget(i)
                tab.min_power.setValue(minPower)
                tab.update_min_power()
