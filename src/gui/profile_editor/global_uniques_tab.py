import contextlib
import copy

from PyQt6.QtCore import QSettings, QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.config.profile_models import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    GlobalUniqueModel,
)
from src.dataloader import Dataloader
from src.gui.importer.gui_common import MAX_POWER
from src.gui.models.checkmark_checkbox import CheckmarkCheckBox
from src.gui.models.dialog import DeleteItem, IgnoreScrollWheelSpinBox
from src.gui.profile_editor.affixes_tab import (
    AffixSummaryWidget,
    CharacterSpinBox,
    ItemTypePicker,
    UniqueAspectWidget,
    _create_column_footer,
    _create_column_header,
    _item_type_summary,
)
from src.item.data.item_type import ItemType, is_armor, is_jewelry, is_weapon

UNIQUES_TABNAME = "GlobalRules"


class UniqueWidget(QWidget):
    duplicate_requested = pyqtSignal(GlobalUniqueModel)

    def __init__(self, unique_model: GlobalUniqueModel, parent=None):
        super().__init__(parent)
        self.settings = QSettings("d4lf", "profile_editor")
        self.unique_model = unique_model
        self.affix_column_widgets = []
        self.affix_pool_layouts = []
        self.affix_footers = []
        self.inherent_footer = None
        self.item_types = [
            item for item in ItemType.__members__.values() if is_armor(item) or is_jewelry(item) or is_weapon(item)
        ]
        self.setup_ui()

    def setup_ui(self):
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(0, 10, 0, 0)

        self.create_general_groupbox()

        # Rule Content
        self.columns_layout = QHBoxLayout()
        self.columns_layout.setContentsMargins(0, 0, 0, 0)
        self.columns_layout.setSpacing(15)

        # Column 1: Unique Aspects
        self.aspect_col, self.aspect_rows_layout, _ = self._create_col_helper("Unique Aspects", self.add_unique_aspect)
        self.columns_layout.addWidget(self.aspect_col)

        # Column(s) 2: Affix Pool(s)
        for pool in self.unique_model.affix_pool:
            self._add_affix_pool_column_widget(pool)

        # Column 3: Inherent Pool (Hidden)
        self.inherent_col, self.inherent_pool_layout, self.inherent_footer = self._create_col_helper(
            "Inherent Pool", self.add_inherent_pool, self.unique_model.inherent_pool[0]
        )
        self.columns_layout.addWidget(self.inherent_col)
        self.inherent_col.hide()

        self.content_layout.addLayout(self.columns_layout)

        # Initialize content
        self.init_aspects()
        self.init_affix_pool()
        self.init_inherent_pool()

    def _create_col_helper(self, title, add_cb, pool_model=None, remove_cb=None):
        col_widget = QWidget()
        col_layout = QVBoxLayout(col_widget)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.setSpacing(0)

        header = _create_column_header(title, add_cb, remove_cb)
        col_layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.viewport().setAutoFillBackground(False)
        scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #2d2d2d; border-left: none; background-color: #121212; border-bottom: none; }"
        )

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(inner)
        col_layout.addWidget(scroll)

        footer = None
        if pool_model is not None:
            footer = _create_column_footer(pool_model, self.update_greater_count_label)
            footer.setStyleSheet(
                "background-color: #1a1a1a; border: 1px solid #2d2d2d; border-left: none; border-top: none;"
            )
            col_layout.addWidget(footer)

        return col_widget, inner_layout, footer

    def _add_affix_pool_column_widget(self, pool_model: AffixFilterCountModel):
        def add_cb():
            self.add_affix_to_pool(pool_model)

        # Only provide a remove callback for additional pools (index > 0)
        is_additional = self.unique_model.affix_pool.index(pool_model) > 0
        remove_cb = (lambda: self.remove_affix_pool_column(pool_model)) if is_additional else None

        col_widget, inner_layout, footer = self._create_col_helper("Affix Pool", add_cb, pool_model, remove_cb)

        # Match the insertion logic in affixes_tab to ensure Aspects are on the left
        # and Affix Pools are in the middle.
        inherent_idx = -1
        if hasattr(self, "inherent_col"):
            inherent_idx = self.columns_layout.indexOf(self.inherent_col)

        insert_idx = inherent_idx if inherent_idx != -1 else self.columns_layout.count()

        self.columns_layout.insertWidget(insert_idx, col_widget)
        self.affix_column_widgets.append(col_widget)
        self.affix_pool_layouts.append(inner_layout)
        self.affix_footers.append(footer)

    def add_additional_affix_pool_column(self):
        new_pool = AffixFilterCountModel(count=[], min_count=1)
        self.unique_model.affix_pool.append(new_pool)
        self._add_affix_pool_column_widget(new_pool)

    def remove_affix_pool_column(self, pool_model: AffixFilterCountModel):
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this entire affix pool?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            idx = self.unique_model.affix_pool.index(pool_model)
            self.unique_model.affix_pool.pop(idx)

            widget = self.affix_column_widgets.pop(idx)
            self.affix_pool_layouts.pop(idx)
            self.affix_footers.pop(idx)

            widget.setParent(None)
            widget.deleteLater()
            self.update_greater_count_label()

    def init_aspects(self):
        for aspect in self.unique_model.unique_aspect:
            self.add_unique_aspect_item(aspect)

    def init_affix_pool(self):
        for i, pool in enumerate(self.unique_model.affix_pool):
            for affix in pool.count:
                self.add_affix_item(affix, inherent=False, pool_idx=i)

    def init_inherent_pool(self):
        for i, pool in enumerate(self.unique_model.inherent_pool):
            for affix in pool.count:
                self.add_affix_item(affix, inherent=True, pool_idx=i)

    def add_affix_item(self, model: AffixFilterModel, inherent: bool = False, pool_idx: int = 0):
        layout = self.inherent_pool_layout if inherent else self.affix_pool_layouts[pool_idx]
        widget = AffixSummaryWidget(model)
        widget.delete_requested.connect(lambda: self.remove_affix_item_widget(widget, inherent, pool_idx))
        widget.config_changed.connect(self.update_greater_count_label)
        layout.addWidget(widget)
        return widget

    def remove_affix_item_widget(self, widget, inherent: bool, pool_idx: int = 0):
        layout = self.inherent_pool_layout if inherent else self.affix_pool_layouts[pool_idx]
        pool = self.unique_model.inherent_pool[0] if inherent else self.unique_model.affix_pool[pool_idx]
        idx = layout.indexOf(widget)
        if idx != -1:
            pool.count.pop(idx)
            widget.setParent(None)
            widget.deleteLater()
            self.update_greater_count_label()

    def create_general_groupbox(self):
        self.general_groupbox = QGroupBox()
        self.general_groupbox.setTitle("Global Unique Rule Configuration")
        self.general_groupbox.setStyleSheet("QGroupBox { border-left: none; border-right: none; }")

        main_vbox = QVBoxLayout(self.general_groupbox)
        main_vbox.setContentsMargins(10, 15, 10, 10)

        # Profile Alias / Name
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Rule Alias:"))
        self.profile_alias = QLineEdit()
        self.profile_alias.setFixedWidth(200)
        self.profile_alias.setStyleSheet("""
            QLineEdit {
                background-color: #09090b;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                color: #e2e8f0;
            }
            QLineEdit:focus { border-color: #3b82f6; }
        """)
        self.profile_alias.setText(self.unique_model.profile_alias)
        self.profile_alias.textChanged.connect(self.update_profile_alias)
        top_row.addWidget(self.profile_alias)

        top_row.addSpacing(30)

        top_row.addWidget(QLabel("Minimum Power:"))
        self.min_power = IgnoreScrollWheelSpinBox()
        self.min_power.setRange(0, MAX_POWER)
        self.min_power.setValue(self.unique_model.min_power)
        self.min_power.setFixedWidth(80)
        self.min_power.valueChanged.connect(self.update_min_power)
        top_row.addWidget(self.min_power)

        top_row.addStretch()

        duplicate_btn = QPushButton("Duplicate Rule")
        duplicate_btn.setFixedWidth(120)
        duplicate_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e3a5f;
                border: 1px solid #3b82f6;
                color: #e2e8f0;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        duplicate_btn.clicked.connect(self._on_duplicate_clicked)
        top_row.addWidget(duplicate_btn)
        main_vbox.addLayout(top_row)

        # Item Types (Slots)
        slots_row = QHBoxLayout()
        slots_row.addWidget(QLabel("Target Slots:"))
        self.item_type_line_edit = QLineEdit()
        self.item_type_line_edit.setReadOnly(True)
        self.refresh_item_type_summary()
        slots_row.addWidget(self.item_type_line_edit)
        edit_item_types_btn = QPushButton("Select Slots")
        edit_item_types_btn.setMaximumWidth(100)
        edit_item_types_btn.clicked.connect(self.edit_item_types)
        slots_row.addWidget(edit_item_types_btn)
        main_vbox.addLayout(slots_row)

        # Min Greater Affixes with Auto Sync
        ga_row = QHBoxLayout()
        ga_row.addWidget(QLabel("Min Greater Affixes:"))
        self.min_greater = CharacterSpinBox()
        self.min_greater.set_range(0, 4)
        self.min_greater.set_value(self.unique_model.min_greater_affix_count)
        self.min_greater.setFixedWidth(100)
        self.min_greater.value_changed.connect(self.update_min_greater_affix_from_spin)

        self.auto_sync_checkbox = CheckmarkCheckBox("Auto Sync")
        self.auto_sync_checkbox.setStyleSheet("background: transparent;")
        self.auto_sync_checkbox.setChecked(
            self.settings.value(f"auto_sync_ga_global_{self.unique_model.profile_alias}", defaultValue=False, type=bool)
        )
        self.auto_sync_checkbox.stateChanged.connect(self.toggle_auto_sync)
        self.greater_count_label = QLabel()
        self.greater_count_label.setStyleSheet("color: gray; font-style: italic;")

        ga_row.addWidget(self.min_greater)
        ga_row.addWidget(self.auto_sync_checkbox)
        ga_row.addWidget(self.greater_count_label)
        ga_row.addStretch()

        add_pool_btn = QPushButton("Add Additional Affix Pool")
        add_pool_btn.setFixedWidth(180)
        add_pool_btn.setStyleSheet("""
            QPushButton {
                background-color: #06201b;
                border: 1px solid #064e3b;
                color: #22c55e;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #064e3b; color: white; }
        """)
        add_pool_btn.clicked.connect(self.add_additional_affix_pool_column)
        ga_row.addWidget(add_pool_btn)
        main_vbox.addLayout(ga_row)

        self.min_greater.setEnabled(not self.auto_sync_checkbox.isChecked())
        self.content_layout.addWidget(self.general_groupbox)

    def _on_duplicate_clicked(self):
        self.duplicate_requested.emit(self.unique_model)

    def add_unique_aspect_item(self, model: AspectUniqueFilterModel) -> UniqueAspectWidget:
        widget = UniqueAspectWidget(model)
        widget.delete_requested.connect(lambda: self.remove_unique_aspect_widget(widget))
        self.aspect_rows_layout.addWidget(widget)
        return widget

    def add_unique_aspect(self):
        aspect_name = next(iter(Dataloader().aspect_unique_dict.keys()))
        new_aspect = AspectUniqueFilterModel(name=aspect_name)
        self.unique_model.unique_aspect.append(new_aspect)
        widget = self.add_unique_aspect_item(new_aspect)
        if widget.open_config_dialog() == QDialog.DialogCode.Rejected:
            self.remove_unique_aspect_widget(widget)

    def remove_unique_aspect_widget(self, widget: UniqueAspectWidget):
        if widget.unique_aspect in self.unique_model.unique_aspect:
            self.unique_model.unique_aspect.remove(widget.unique_aspect)
        widget.setParent(None)
        widget.deleteLater()

    def add_affix_to_pool(self, pool_model: AffixFilterCountModel):
        idx = self.unique_model.affix_pool.index(pool_model)
        affix_name = next(iter(Dataloader().affix_dict.keys()))
        new_affix = AffixFilterModel(name=affix_name)
        pool_model.count.append(new_affix)
        widget = self.add_affix_item(new_affix, pool_idx=idx)
        if widget.open_config_dialog() == QDialog.DialogCode.Rejected:
            self.remove_affix_item_widget(widget, inherent=False, pool_idx=idx)

    def add_affix_pool(self):
        if self.unique_model.affix_pool:
            self.add_affix_to_pool(self.unique_model.affix_pool[0])

    def add_inherent_pool(self):
        affix_name = next(iter(Dataloader().affix_dict.keys()))
        new_affix = AffixFilterModel(name=affix_name)
        self.unique_model.inherent_pool[0].count.append(new_affix)
        widget = self.add_affix_item(new_affix, inherent=True)
        if widget.open_config_dialog() == QDialog.DialogCode.Rejected:
            self.remove_affix_item_widget(widget, inherent=True)

    def toggle_auto_sync(self):
        is_auto = self.auto_sync_checkbox.isChecked()
        self.settings.setValue(f"auto_sync_ga_global_{self.unique_model.profile_alias}", is_auto)
        self.min_greater.setEnabled(not is_auto)
        if is_auto:
            self.update_greater_count_label()

    def update_greater_count_label(self):
        count = 0
        # Count in affix pools
        for pool in self.unique_model.affix_pool:
            for affix in pool.count:
                if getattr(affix, "want_greater", False):
                    count += 1

        if count == 0:
            self.greater_count_label.setText("(no greater affixes marked)")
        else:
            self.greater_count_label.setText(f"({count} GAs required)")
            if self.auto_sync_checkbox.isChecked():
                with QSignalBlocker(self.min_greater):
                    self.min_greater.set_value(count)

        # Update affix pool footers
        for footer, model in zip(self.affix_footers, self.unique_model.affix_pool, strict=False):
            self._update_footer_constraints(footer, model)

        # Update inherent pool footer
        self._update_footer_constraints(self.inherent_footer, self.unique_model.inherent_pool[0])

    def _update_footer_constraints(self, footer, model):
        if footer and model:
            min_spin = footer.property("min_spin")
            if min_spin:
                min_allowed = sum(1 for a in model.count if getattr(a, "required", False))
                min_spin.set_minimum(min_allowed)
                if model.min_count < min_allowed:
                    model.min_count = min_allowed
                    min_spin.set_value(min_allowed)

    def refresh_item_type_summary(self):
        self.item_type_line_edit.setText(_item_type_summary(self.unique_model.item_type))

    def edit_item_types(self):
        picker = ItemTypePicker(self, self.item_types, self.unique_model.item_type)
        if picker.exec() == QDialog.DialogCode.Accepted:
            self.unique_model.item_type = picker.get_selected_item_types()
            self.refresh_item_type_summary()

    def update_profile_alias(self, value: str):
        self.unique_model.profile_alias = value.strip()
        self.update_parent_tab_text()

    def update_parent_tab_text(self):
        p = self.parent()
        while p:
            if type(p).__name__ == "UniquesTab":
                p.rename_tabs()
                break
            p = p.parent()

    def update_min_power(self):
        self.unique_model.min_power = self.min_power.value()

    def update_min_greater_affix(self):
        self.unique_model.min_greater_affix_count = self.min_greater.value()

    def update_min_greater_affix_from_spin(self, value: int):
        self.unique_model.min_greater_affix_count = value


class UniquesTab(QWidget):
    def __init__(self, unique_model_list: list[GlobalUniqueModel], parent=None):
        super().__init__(parent)
        self.unique_model_list = unique_model_list
        self._current_slot_name = ""
        self._current_slot_item_types = []
        self.loaded = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def load(self):
        with contextlib.suppress(RuntimeError):
            if not self.loaded:
                self.setup_ui()
                self.loaded = True

    def setup_ui(self):
        self.setStyleSheet("background: transparent; border: none;")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setStyleSheet("""
            QTabWidget { background: transparent; }
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: #1a1a1a;
                color: #94a3b8;
                padding: 8px 24px 8px 12px;
                border: 1px solid #334155;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::close-button:hover { background-color: rgba(255, 255, 255, 0.1); }
            QTabBar::tab:selected {
                background: #1e3a5f;
                color: #e2e8f0;
                border: 1px solid #3b82f6;
                border-bottom: 2px solid #3b82f6;
            }
            QTabBar::tab:last, QTabBar::tab:selected:last, QTabBar::tab:only-one, QTabBar::tab:selected:only-one {
                background: #06201b;
                color: #22c55e;
                border: 1px solid #064e3b;
                border-bottom: 1px solid #064e3b;
            }
        """)
        with QSignalBlocker(self.tab_widget):
            self.tab_widget.setTabsClosable(True)
            self.tab_widget.tabCloseRequested.connect(self.close_tab)
            self.tab_widget.currentChanged.connect(self._on_tab_changed)
            self.tab_widget.tabBar().tabBarClicked.connect(self._on_tab_bar_clicked)

            # Add a persistent "+" tab at the end
            self.tab_widget.addTab(QWidget(), "+")

            for i, unique_model in enumerate(self.unique_model_list):
                self.tab_widget.insertTab(
                    self.tab_widget.count() - 1, QWidget(), unique_model.profile_alias or f"Rule {i}"
                )

        self._update_plus_tab_button()

        self.main_layout.addWidget(self.tab_widget)

    def _on_tab_changed(self, index):
        if index >= 0 and self.tab_widget.tabText(index) == "+":
            self.add_item_type()

    def _on_tab_bar_clicked(self, index):
        # This handles clicking the "+" tab when it's already selected
        if index >= 0 and self.tab_widget.tabText(index) == "+" and self.tab_widget.currentIndex() == index:
            self.add_item_type()

    def _update_plus_tab_button(self):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "+":
                self.tab_widget.tabBar().setTabButton(i, QTabBar.ButtonPosition.RightSide, None)
                self.tab_widget.setTabToolTip(i, "Create Rule")

    def close_tab(self, index):
        if self.tab_widget.tabText(index) == "+":
            return

        rule_name = self.tab_widget.tabText(index)
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the global rule '{rule_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        with QSignalBlocker(self.tab_widget):
            self.tab_widget.removeTab(index)
            self.unique_model_list.pop(index)
        self.rename_tabs()
        self._update_plus_tab_button()

    def filter_by_item_types(self, item_types: list[ItemType] | None, slot_name: str | None = None):
        """Show only tabs that match the provided item types."""
        if not hasattr(self, "tab_widget"):
            return
        self._current_slot_name = slot_name
        self._current_slot_item_types = item_types

        with QSignalBlocker(self.tab_widget):
            if slot_name is None:  # Global Rules view
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.tabText(i) == "+":
                        self.tab_widget.setTabVisible(i, True)  # noqa: FBT003
                        continue
                    self._ensure_tab_instantiated(i)
                    self.tab_widget.setTabVisible(i, True)  # noqa: FBT003
                return

            slot_match_name = slot_name.lower().replace(" ", "").replace("-", "") if slot_name else None
            is_rings = slot_match_name == "rings"
            is_dw_all = slot_match_name == "dualwields"
            is_ring_2 = slot_match_name == "ring2"
            is_ring_1 = slot_match_name == "ring1"
            is_dw_1 = slot_match_name == "dualwield1"
            is_dw_2 = slot_match_name == "dualwield2"
            is_dw_ranged = slot_match_name == "rangedweapon"
            is_bludgeoning = slot_match_name == "bludgeoning"
            is_slashing = slot_match_name == "slashing"
            is_main_hand = slot_match_name == "mainhand"
            type_names = [t.value.lower().replace(" ", "").replace("-", "") for t in item_types] if item_types else []

            # Check for exact matches in rule aliases/names
            has_exact_match = False
            if slot_match_name:
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.tabText(i) == "+":
                        continue
                    model = self.unique_model_list[i]
                    alias = model.profile_alias.lower().replace(" ", "").replace("-", "")
                    if (
                        alias == slot_match_name
                        or (slot_match_name and slot_match_name in alias)
                        or (alias and alias in slot_match_name)
                        or (is_rings and "ring" in alias)
                        or (is_dw_all and "dualwield" in alias)
                        or (is_ring_1 and alias == "ring")
                        or (is_dw_1 and alias == "dualwield")
                        or (is_dw_2 and alias == "dualwield")
                        or (is_dw_ranged and alias == "ranged")
                        or (
                            alias in type_names
                            and not (is_ring_2 or is_dw_2 or is_dw_1 or is_bludgeoning or is_slashing or is_dw_ranged)
                        )
                        or (is_main_hand and alias == "weapon")
                    ):
                        has_exact_match = True
                        break

            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "+":
                    self.tab_widget.setTabVisible(i, True)  # noqa: FBT003
                    continue

                model = self.unique_model_list[i]
                alias = model.profile_alias.lower().replace(" ", "").replace("-", "")
                rule_types = getattr(model, "item_type", [])
                type_match = not item_types or not rule_types or any(t in rule_types for t in item_types)

                if has_exact_match:
                    visible = type_match and (
                        alias == slot_match_name
                        or (slot_match_name and slot_match_name in alias)
                        or (alias and alias in slot_match_name)
                        or (is_rings and "ring" in alias)
                        or (is_dw_all and "dualwield" in alias)
                        or (is_ring_1 and alias == "ring")
                        or (is_dw_1 and alias == "dualwield")
                        or (is_dw_2 and alias == "dualwield")
                        or (is_dw_ranged and alias == "ranged")
                        or (
                            alias in type_names
                            and not (is_ring_2 or is_dw_2 or is_dw_1 or is_bludgeoning or is_slashing or is_dw_ranged)
                        )
                        or (is_main_hand and alias == "weapon")
                    )
                else:
                    visible = type_match

                if visible:
                    self._ensure_tab_instantiated(i)
                self.tab_widget.setTabVisible(i, visible)

            # Ensure a valid content tab is focused instead of the '+' tab
            curr = self.tab_widget.currentIndex()
            if curr == -1 or not self.tab_widget.isTabVisible(curr) or self.tab_widget.tabText(curr) == "+":
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.isTabVisible(i) and self.tab_widget.tabText(i) != "+":
                        self.tab_widget.setCurrentIndex(i)
                        break

    def _ensure_tab_instantiated(self, index: int):
        if index < 0 or index >= self.tab_widget.count():
            return
        if not isinstance(self.tab_widget.widget(index), UniqueWidget):
            # Find the correct model by counting non-plus tabs before this one
            model_idx = 0
            for i in range(index):
                if self.tab_widget.tabText(i) != "+":
                    model_idx += 1

            if model_idx >= len(self.unique_model_list):
                return

            model = self.unique_model_list[model_idx]
            widget = UniqueWidget(model)
            widget.duplicate_requested.connect(self.duplicate_rule_tab)
            name = self.tab_widget.tabText(index)
            is_current = self.tab_widget.currentIndex() == index
            with QSignalBlocker(self.tab_widget):
                self.tab_widget.removeTab(index)
                self.tab_widget.insertTab(index, widget, name)
                if is_current:
                    self.tab_widget.setCurrentIndex(index)

    def duplicate_rule_tab(self, original_model: GlobalUniqueModel):
        # Find a unique alias for the duplicated rule
        original_alias = original_model.profile_alias or "New Rule"
        new_alias_base = f"{original_alias} (Copy)"
        new_alias = new_alias_base

        existing_aliases = [m.profile_alias for m in self.unique_model_list]
        i = 1
        while new_alias in existing_aliases:
            i += 1
            new_alias = f"{new_alias_base} {i}"

        # Create a deep copy of the unique rule model
        new_model = copy.deepcopy(original_model)
        new_model.profile_alias = new_alias
        self.unique_model_list.append(new_model)

        plus_idx = -1
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "+":
                plus_idx = i
                break

        # Create the actual editor widget and insert the tab
        editor = UniqueWidget(new_model)
        editor.duplicate_requested.connect(self.duplicate_rule_tab)

        if plus_idx != -1:
            self.tab_widget.insertTab(plus_idx, editor, new_alias)
            self.tab_widget.setCurrentIndex(plus_idx)
        self._update_plus_tab_button()

    def remove_item_type(self):
        dialog = DeleteItem([self.tab_widget.tabText(i) for i in range(self.tab_widget.count())], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item_names_to_delete = dialog.get_value()
            to_delete_index = [
                i for i in range(self.tab_widget.count()) if self.tab_widget.tabText(i) in item_names_to_delete
            ]
            to_delete_index.reverse()
            for index in to_delete_index:
                self.tab_widget.removeTab(index)
                self.unique_model_list.pop(index)
            self.rename_tabs()
            self._update_plus_tab_button()
            return

    def rename_tabs(self):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "+":
                continue
            model = self.unique_model_list[i]
            self.tab_widget.setTabText(i, model.profile_alias or f"Rule {i}")

    def add_item_type(self):
        item_types = self._current_slot_item_types or []
        plus_idx = -1
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "+":
                plus_idx = i
                break

        # Switch to previous tab if we were triggered by clicking the "+" tab
        if self.tab_widget.currentIndex() == plus_idx and plus_idx > 0:
            self.tab_widget.setCurrentIndex(plus_idx - 1)

        alias = f"New Rule {self.tab_widget.count()}"
        unique_model = GlobalUniqueModel(item_type=item_types, profileAlias=alias)
        group = UniqueWidget(unique_model)
        group.duplicate_requested.connect(self.duplicate_rule_tab)
        self.tab_widget.insertTab(plus_idx, group, alias)
        self.unique_model_list.append(unique_model)
        self.tab_widget.setCurrentIndex(plus_idx)
        self._update_plus_tab_button()
