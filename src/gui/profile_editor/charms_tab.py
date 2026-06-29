import logging

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtWidgets import (
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

from src.config.profile_models import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    DynamicCharmFilterModel,
)
from src.dataloader import Dataloader
from src.gui.models.collapsible_widget import Container
from src.gui.models.dialog import (
    CreateCharmOrSeal,
    DeleteAffixPool,
    DeleteItem,
    MinGreaterDialog,
    MinPercentDialog,
    RarityPicker,
    SetPicker,
    rarity_summary,
)
from src.gui.profile_editor.affixes_tab import UNIQUE_ASPECTS_TITLE, AffixPoolWidget, AffixWidget, UniqueAspectWidget

LOGGER = logging.getLogger(__name__)

CHARMS_TABNAME = "Charms"


def _set_summary(sets: list[str]) -> str:
    if not sets:
        return "No sets selected"
    return ", ".join(sets)


class CharmGroupEditor(QWidget):
    """Editor widget for a single named charm filter."""

    def __init__(self, dynamic_filter: DynamicCharmFilterModel, parent=None):
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

        # Rarities
        self.rarity_line_edit = _create_readonly_line_edit()
        self.refresh_rarity_summary()

        rarity_layout = QHBoxLayout()
        rarity_layout.addWidget(self.rarity_line_edit)
        edit_rarities_btn = QPushButton("...")
        edit_rarities_btn.setMaximumWidth(40)
        edit_rarities_btn.clicked.connect(self.edit_rarities)
        rarity_layout.addWidget(edit_rarities_btn)
        rarity_layout.addStretch()
        general_form.addRow("Rarities:", rarity_layout)

        # Set names (charm-specific)
        self.set_line_edit = _create_readonly_line_edit()
        self.refresh_set_summary()

        set_layout = QHBoxLayout()
        set_layout.addWidget(self.set_line_edit)
        edit_sets_btn = QPushButton("...")
        edit_sets_btn.setMaximumWidth(40)
        edit_sets_btn.clicked.connect(self.edit_sets)
        set_layout.addWidget(edit_sets_btn)
        set_layout.addStretch()
        general_form.addRow("Sets:", set_layout)

        # Min Greater Affixes
        min_greater_layout = QHBoxLayout()

        self.min_greater = QSpinBox()
        self.min_greater.setValue(self.config.min_greater_affix_count)
        self.min_greater.setMaximum(4)
        self.min_greater.setMinimum(0)
        self.min_greater.setMaximumWidth(80)
        self.min_greater.setToolTip(
            "Minimum number of checked affixes that must be Greater Affixes.\n"
            "0 = Accept items even without GAs (for leveling)\n"
            "1-4 = At least this many checked affixes must be GA"
        )
        self.min_greater.valueChanged.connect(self.update_min_greater_affix)

        self.auto_sync_checkbox = _create_auto_sync_checkbox()
        self.auto_sync_checkbox.setChecked(
            self.settings.value(f"auto_sync_ga_{self.item_name}", defaultValue=False, type=bool)
        )
        self.auto_sync_checkbox.stateChanged.connect(self.toggle_auto_sync)

        self.greater_count_label = QLabel()
        self.greater_count_label.setProperty("greaterCountLabel", True)  # noqa: FBT003
        _refresh_widget_style(self.greater_count_label)
        self.update_greater_count_label()

        min_greater_layout.addWidget(self.min_greater)
        min_greater_layout.addWidget(self.auto_sync_checkbox)
        min_greater_layout.addWidget(self.greater_count_label)
        min_greater_layout.addStretch()

        self.min_greater.setEnabled(not self.auto_sync_checkbox.isChecked())

        if self.auto_sync_checkbox.isChecked():
            self.min_greater.setProperty("autoSyncSpin", True)  # noqa: FBT003
            _refresh_widget_style(self.min_greater)

        general_form.addRow("Min Greater Affixes:", min_greater_layout)

        self.content_layout.addLayout(general_form)
        self.create_unique_aspect_container()

        # Affix Pool (no inherent pool for charms)
        pool_btn_layout = QHBoxLayout()
        add_affix_pool_btn = QPushButton("Add Affix Pool")
        add_affix_pool_btn.clicked.connect(self.add_affix_pool)
        remove_affix_pool_btn = QPushButton("Remove Affix Pool")
        remove_affix_pool_btn.clicked.connect(lambda: self.remove_selected(self.affix_pool_layout))

        pool_btn_layout.addWidget(add_affix_pool_btn)
        pool_btn_layout.addWidget(remove_affix_pool_btn)

        self.affix_pool_container = Container("Affix Pool")
        self.affix_pool_layout = QVBoxLayout(self.affix_pool_container.content_widget)
        self.affix_pool_container.first_expansion.connect(self.init_affix_pool)

        self.content_layout.addWidget(self.affix_pool_container)
        self.content_layout.addLayout(pool_btn_layout)

        scroll_area.setWidget(content_widget)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

        QTimer.singleShot(100, self.affix_pool_container.expand)

    # --- Sets (charm-specific) ---

    def refresh_set_summary(self):
        self.set_line_edit.setText(_set_summary(self.config.set))

    def edit_sets(self):
        if self.config.unique_aspect:
            QMessageBox.warning(
                self, "Warning", "Cannot define both set and unique aspect. Remove unique aspects first."
            )
            return
        set_picker = SetPicker(self, self.config.set)
        if set_picker.exec() == QDialog.DialogCode.Accepted:
            self.config.set = set_picker.get_selected_sets()
            self.refresh_set_summary()

    # --- Unique Aspects ---

    def create_unique_aspect_container(self):
        self.unique_aspect_container = Container(self._unique_aspects_title())
        self.unique_aspect_layout = QVBoxLayout(self.unique_aspect_container.content_widget)
        self.unique_aspect_container.first_expansion.connect(self.init_unique_aspects)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        aspect_label = QLabel("Aspect")
        aspect_label.setProperty("affixHeaderLabel", True)  # noqa: FBT003
        _refresh_widget_style(aspect_label)

        mode_label = QLabel("Mode")
        mode_label.setProperty("affixHeaderLabel", True)  # noqa: FBT003
        _refresh_widget_style(mode_label)

        value_label = QLabel("Threshold")
        value_label.setProperty("affixHeaderLabel", True)  # noqa: FBT003
        _refresh_widget_style(value_label)

        title_layout.addSpacing(25)
        title_layout.addWidget(aspect_label)
        title_layout.addSpacing(440)
        title_layout.addWidget(mode_label)
        title_layout.addSpacing(85)
        title_layout.addWidget(value_label)

        self.unique_aspect_list = QListWidget()
        self.unique_aspect_list.setFixedHeight(180)
        self.unique_aspect_list.setAlternatingRowColors(True)
        self.unique_aspect_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.unique_aspect_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        unique_aspect_btn_layout = QHBoxLayout()
        add_unique_aspect_btn = QPushButton("Add Unique Aspect")
        add_unique_aspect_btn.clicked.connect(self.add_unique_aspect)
        unique_aspect_btn_layout.addWidget(add_unique_aspect_btn)

        remove_unique_aspect_btn = QPushButton("Remove Unique Aspect")
        remove_unique_aspect_btn.clicked.connect(self.remove_selected_unique_aspects)
        unique_aspect_btn_layout.addWidget(remove_unique_aspect_btn)

        layout.addLayout(unique_aspect_btn_layout)
        layout.addLayout(title_layout)
        layout.addWidget(self.unique_aspect_list)

        self.unique_aspect_layout.addLayout(layout)
        self.content_layout.addWidget(self.unique_aspect_container)

    def _unique_aspects_title(self):
        aspect_names = ", ".join(unique_aspect.name for unique_aspect in self.config.unique_aspect) or "None"
        return f"{UNIQUE_ASPECTS_TITLE} - {aspect_names}"

    def refresh_unique_aspects_title(self):
        self.unique_aspect_container.header.set(self._unique_aspects_title())

    def init_unique_aspects(self):
        for unique_aspect in self.config.unique_aspect:
            self.add_unique_aspect_item(unique_aspect)

    def add_unique_aspect_item(self, unique_aspect: AspectUniqueFilterModel):
        item = QListWidgetItem()
        widget = UniqueAspectWidget(unique_aspect)
        item_size = widget.sizeHint()
        item_size.setWidth(850)
        item.setSizeHint(item_size)
        self.unique_aspect_list.addItem(item)
        self.unique_aspect_list.setItemWidget(item, widget)

    def add_unique_aspect(self):
        if self.config.set:
            QMessageBox.warning(self, "Warning", "Cannot define both set and unique aspect. Remove sets first.")
            return
        existing_names = {unique_aspect.name for unique_aspect in self.config.unique_aspect}
        for aspect_name in Dataloader().aspect_unique_dict:
            if aspect_name in existing_names:
                continue
            new_unique_aspect = AspectUniqueFilterModel(name=aspect_name, value=None)
            self.config.unique_aspect.append(new_unique_aspect)
            self.add_unique_aspect_item(new_unique_aspect)
            self.refresh_unique_aspects_title()
            return
        QMessageBox.information(self, "Info", "All unique aspects have already been added.")

    def remove_selected_unique_aspects(self):
        selected_rows = sorted(
            (self.unique_aspect_list.row(item) for item in self.unique_aspect_list.selectedItems()), reverse=True
        )
        for row in selected_rows:
            self.unique_aspect_list.takeItem(row)
            del self.config.unique_aspect[row]
        self.refresh_unique_aspects_title()

    # --- Affix Pool ---

    def init_affix_pool(self):
        """Initialize affix pool content on first expansion."""
        for pool in self.config.affix_pool:
            self.add_affix_pool_item(pool)
        QTimer.singleShot(50, self.update_greater_count_label)

    def add_affix_pool_item(self, pool: AffixFilterCountModel):
        nb_count = self.affix_pool_layout.count()
        container = Container(f"Count {nb_count}", color_background=True)
        container_layout = QVBoxLayout(container.content_widget)
        widget = AffixPoolWidget(pool, self)
        container_layout.addWidget(widget)
        self.affix_pool_layout.addWidget(container)
        QTimer.singleShot(50, container.expand)

    def add_affix_pool(self):
        default_affix = AffixFilterModel(name=next(iter(Dataloader().charm_affix_dict.keys())), value=None)
        new_pool = AffixFilterCountModel(count=[default_affix], min_count=1, max_count=3)
        self.config.affix_pool.append(new_pool)
        self.add_affix_pool_item(new_pool)

    def remove_selected(self, layout_widget: QVBoxLayout):
        nb_pool = layout_widget.count()
        dialog = DeleteAffixPool(nb_pool)
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
                self.config.affix_pool.pop(index)
            self.reorganize_pool(layout_widget)

    def reorganize_pool(self, layout_widget: QVBoxLayout):
        for i in range(layout_widget.count()):
            item = layout_widget.itemAt(i)
            if item and item.widget() is not None:
                item.widget().header.set(f"Count {i}")

    # --- Rarities ---

    def refresh_rarity_summary(self):
        self.rarity_line_edit.setText(rarity_summary(self.config.rarities))

    def edit_rarities(self):
        rarity_picker = RarityPicker(self, self.config.rarities)
        if rarity_picker.exec() == QDialog.DialogCode.Accepted:
            self.config.rarities = rarity_picker.get_selected_rarities()
            self.refresh_rarity_summary()

    # --- Greater Affix Auto-Sync ---

    def update_min_greater_affix(self):
        self.config.min_greater_affix_count = self.min_greater.value()

    def toggle_auto_sync(self):
        is_auto_sync = self.auto_sync_checkbox.isChecked()
        self.settings.setValue(f"auto_sync_ga_{self.item_name}", is_auto_sync)
        self.min_greater.setEnabled(not is_auto_sync)

        if is_auto_sync:
            self.min_greater.setProperty("autoSyncSpin", True)  # noqa: FBT003
            _refresh_widget_style(self.min_greater)
            self.affix_pool_container.expand()
            count = self.count_want_greater_affixes()
            self.min_greater.setValue(count)
            self.update_greater_count_label()
        else:
            self.min_greater.setProperty("autoSyncSpin", False)  # noqa: FBT003
            _refresh_widget_style(self.min_greater)

    def sync_min_greater_from_checkboxes(self):
        if self.auto_sync_checkbox.isChecked():
            count = self.count_want_greater_affixes()
            self.min_greater.setValue(count)

    def _ensure_pool_widgets_initialized(self):
        was_visible = self.affix_pool_container.content_widget.isVisible()
        if self.affix_pool_container.header.first_expansion:
            self.affix_pool_container.expand()
            if not was_visible:
                self.affix_pool_container.collapse()

    def iter_affix_widgets(self):
        self._ensure_pool_widgets_initialized()
        for i in range(self.affix_pool_layout.count()):
            container = self.affix_pool_layout.itemAt(i).widget()
            if container is None or not hasattr(container, "content_widget"):
                continue
            pool_item = container.content_widget.layout().itemAt(0)
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
        if not hasattr(self, "affix_pool_layout"):
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


class CharmsTab(QWidget):
    def __init__(self, charms_model: list[DynamicCharmFilterModel], parent=None):
        super().__init__(parent)
        self.charms_model = charms_model
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

        self.toolbar = QToolBar("CharmsToolBar", self)
        self.toolbar.setMinimumHeight(50)
        self.toolbar.setContentsMargins(10, 10, 10, 10)
        self.toolbar.setMovable(False)

        self.item_names = []
        for charm_group in self.charms_model:
            for item_name in charm_group.root:
                if item_name in self.item_names:
                    QMessageBox.warning(
                        self, "Warning", f"Charm name already exists, please rename {item_name} in the profile file."
                    )
                    continue
                group = CharmGroupEditor(charm_group)
                self.item_names.append(item_name)
                self.tab_widget.addTab(group, item_name)

        add_item_button = QPushButton()
        add_item_button.setText("Create Charm")
        add_item_button.clicked.connect(self.add_item_type)

        remove_item_button = QPushButton()
        remove_item_button.setText("Remove Charm")
        remove_item_button.clicked.connect(self.remove_item_type)

        set_all_min_greater_affix_button = QPushButton("Set All Min GAs (Excludes Auto Synced Items)")
        convert_all_to_min_percent_button = QPushButton("Convert All To Min %")
        set_all_min_greater_affix_button.clicked.connect(self.set_all_min_greater_affix)
        convert_all_to_min_percent_button.clicked.connect(self.convert_all_to_min_percent_of_affix)

        self.toolbar.addWidget(add_item_button)
        self.toolbar.addWidget(remove_item_button)
        self.toolbar.addWidget(set_all_min_greater_affix_button)
        self.toolbar.addWidget(convert_all_to_min_percent_button)

        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addWidget(self.tab_widget)

    def add_item_type(self):
        dialog = CreateCharmOrSeal(self.item_names, is_charm=True, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item = dialog.get_value()
            for item_name in item.root:
                group = CharmGroupEditor(item)
                self.item_names.append(item_name)
                self.tab_widget.addTab(group, item_name)
                self.charms_model.append(item)
            return

    def close_tab(self, index):
        self.item_names.pop(index)
        self.tab_widget.removeTab(index)
        self.charms_model.pop(index)

    def remove_item_type(self):
        dialog = DeleteItem(self.item_names, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item_names_to_delete = dialog.get_value()
            for item_name in item_names_to_delete:
                index = self.item_names.index(item_name)
                self.item_names.remove(item_name)
                self.tab_widget.removeTab(index)
                self.charms_model.pop(index)
            return

    def set_all_min_greater_affix(self):
        dialog = MinGreaterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            min_greater_affix = dialog.get_value()
            for i in range(self.tab_widget.count()):
                tab: CharmGroupEditor = self.tab_widget.widget(i)
                if tab.auto_sync_checkbox.isChecked():
                    continue
                tab.min_greater.setValue(min_greater_affix)
                tab.update_min_greater_affix()

    def convert_all_to_min_percent_of_affix(self):
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, CharmGroupEditor):
            dialog = MinPercentDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                current_tab.convert_all_to_min_percent_of_affix(dialog.get_value())


# --- Helpers ---


def _create_readonly_line_edit():
    line_edit = QLineEdit()
    line_edit.setReadOnly(True)
    line_edit.setMinimumWidth(360)
    line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return line_edit


def _create_auto_sync_checkbox():
    from PyQt6.QtWidgets import QCheckBox  # noqa: PLC0415

    checkbox = QCheckBox("Auto Sync")
    checkbox.setToolTip(
        "When checked: Min Greater Affixes automatically matches the number of affixes marked as 'want greater'\n"
        "When unchecked: You can manually set Min Greater Affixes to any value"
    )
    return checkbox


def _refresh_widget_style(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
