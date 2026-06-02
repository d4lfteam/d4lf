from functools import partial

from PyQt6.QtCore import QSignalBlocker, Qt, QTimer
from PyQt6.QtGui import QDoubleValidator, QIntValidator
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.config.profile_models import (
    AffixFilterCountModel,
    AffixFilterModel,
    BoostedSetFilterModel,
    CharmFilterModel,
    DynamicCharmFilterModel,
    DynamicSealCharmFilterModel,
    DynamicSealFilterModel,
    SealCharmFilterModel,
    SealFilterModel,
)
from src.dataloader import Dataloader
from src.gui.models.collapsible_widget import Container
from src.gui.models.dialog import DeleteAffixPool, DeleteItem, IgnoreScrollWheelComboBox
from src.gui.profile_editor.affixes_tab import AffixPoolWidget
from src.item.data.rarity import ItemRarity
from src.scripts import correct_name

SEALS_TABNAME = "Seals"
CHARMS_TABNAME = "Charms"
AFFIX_VALUE_MODE = "Value"
AFFIX_PERCENT_MODE = "Min %"
BOOSTED_SET_SLOT_COUNT = 2


class SealCharmRuleEditor(QWidget):
    def __init__(self, dynamic_filter: DynamicSealCharmFilterModel, parent=None):
        super().__init__(parent)
        for rule_name, config in dynamic_filter.root.items():
            self.rule_name = rule_name
            self.config = config
        self.setup_ui()

    def setup_ui(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        general_form = QFormLayout()
        self.min_greater = QSpinBox()
        self.min_greater.setRange(0, 4)
        self.min_greater.setValue(self.config.min_greater_affix_count)
        self.min_greater.valueChanged.connect(self.update_min_greater_affix)
        general_form.addRow("Min Greater Affixes:", self.min_greater)

        rarity_layout = QHBoxLayout()
        self.rarity_checkboxes = {}
        selected_rarities = set(self.config.rarities)
        for rarity in ItemRarity:
            checkbox = QCheckBox(rarity.name)
            checkbox.setChecked(rarity in selected_rarities)
            checkbox.stateChanged.connect(self.update_rarities)
            self.rarity_checkboxes[rarity] = checkbox
            rarity_layout.addWidget(checkbox)
        rarity_layout.addStretch()
        general_form.addRow("Rarities:", rarity_layout)
        if isinstance(self.config, SealFilterModel):
            self.add_boosted_set_fields(general_form)
        self.content_layout.addLayout(general_form)

        pool_btn_layout = QHBoxLayout()
        add_affix_pool_btn = QPushButton("Add Affix Pool")
        add_affix_pool_btn.clicked.connect(self.add_affix_pool)
        remove_affix_pool_btn = QPushButton("Remove Affix Pool")
        remove_affix_pool_btn.clicked.connect(self.remove_selected)
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

    def add_boosted_set_fields(self, form: QFormLayout):
        charm_slots_layout = QHBoxLayout()
        self.charm_slot_checkboxes = {}
        for slots in range(1, 7):
            checkbox = QCheckBox(str(slots))
            checkbox.setChecked(self.config.charm_slots == slots)
            checkbox.clicked.connect(partial(self.update_charm_slots, slots))
            self.charm_slot_checkboxes[slots] = checkbox
            charm_slots_layout.addWidget(checkbox)
        charm_slots_layout.addStretch()
        form.addRow("Charm Slots:", charm_slots_layout)

        boosted_set_filters = list(self.config.boosted_sets)
        if self.config.boosted_set:
            boosted_set_filters.append(
                BoostedSetFilterModel(
                    set=self.config.boosted_set,
                    affix=self.config.boosted_affix,
                    required=self.config.boosted_affix_required,
                )
            )
            self.config.boosted_set = None
            self.config.boosted_affix = None
            self.config.boosted_affix_required = False
            self.config.boosted_sets = boosted_set_filters

        self.boosted_set_combos = []
        self.boosted_affix_combos = []
        self.boosted_affix_required_checkboxes = []
        self.boosted_affix_modes = []
        self.boosted_affix_values = []

        for index in range(BOOSTED_SET_SLOT_COUNT):
            boosted_set_filter = boosted_set_filters[index] if index < len(boosted_set_filters) else None

            boosted_set_combo = IgnoreScrollWheelComboBox()
            boosted_set_combo.setEditable(True)
            boosted_set_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            boosted_set_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            boosted_set_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
            boosted_set_combo.addItems(["", *sorted(Dataloader().set_list)])
            if boosted_set_filter:
                boosted_set_combo.setCurrentText(boosted_set_filter.set_name)

            boosted_affix_combo = IgnoreScrollWheelComboBox()
            boosted_affix_combo.setEditable(True)
            boosted_affix_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            boosted_affix_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            boosted_affix_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
            boosted_affix_combo.addItems(["", *sorted(Dataloader().affix_dict.values())])
            if (
                boosted_set_filter
                and boosted_set_filter.affix
                and boosted_set_filter.affix.name in Dataloader().affix_dict
            ):
                boosted_affix_combo.setCurrentText(Dataloader().affix_dict[boosted_set_filter.affix.name])

            boosted_affix_required = QCheckBox()
            boosted_affix_required.setChecked(bool(boosted_set_filter and boosted_set_filter.required))

            boosted_affix_mode = IgnoreScrollWheelComboBox()
            boosted_affix_mode.setFixedSize(100, boosted_affix_mode.sizeHint().height())
            boosted_affix_mode.addItems([AFFIX_VALUE_MODE, AFFIX_PERCENT_MODE])
            if boosted_set_filter and boosted_set_filter.affix and boosted_set_filter.affix.min_percent_of_affix:
                boosted_affix_mode.setCurrentText(AFFIX_PERCENT_MODE)

            boosted_affix_value = QLineEdit()
            boosted_affix_value.setFixedSize(100, boosted_affix_value.sizeHint().height())

            self.boosted_set_combos.append(boosted_set_combo)
            self.boosted_affix_combos.append(boosted_affix_combo)
            self.boosted_affix_required_checkboxes.append(boosted_affix_required)
            self.boosted_affix_modes.append(boosted_affix_mode)
            self.boosted_affix_values.append(boosted_affix_value)

            form.addRow(f"Boosted Set {index + 1}:", boosted_set_combo)
            form.addRow(f"Boosted Affix {index + 1}:", boosted_affix_combo)
            form.addRow(f"Require Boosted Affix {index + 1}:", boosted_affix_required)

            boosted_affix_threshold_layout = QHBoxLayout()
            boosted_affix_threshold_layout.addWidget(boosted_affix_mode)
            boosted_affix_threshold_layout.addWidget(boosted_affix_value)
            boosted_affix_threshold_layout.addStretch()
            form.addRow(f"Boosted Affix Threshold {index + 1}:", boosted_affix_threshold_layout)

            boosted_set_combo.currentTextChanged.connect(partial(self.update_boosted_set, index))
            boosted_affix_combo.currentTextChanged.connect(partial(self.update_boosted_affix, index))
            boosted_affix_required.clicked.connect(partial(self.update_boosted_affix_required, index))
            boosted_affix_mode.currentTextChanged.connect(partial(self.update_boosted_affix_mode, index))
            boosted_affix_value.textChanged.connect(partial(self.update_boosted_affix_value, index))
            self.refresh_boosted_affix_controls(index)

    def init_affix_pool(self):
        for pool in self.config.affix_pool:
            self.add_affix_pool_item(pool)

    def add_affix_pool_item(self, pool: AffixFilterCountModel):
        nb_count = self.affix_pool_layout.count()
        container = Container(f"Count {nb_count}", color_background=True)
        container_layout = QVBoxLayout(container.content_widget)
        widget = AffixPoolWidget(pool)
        container_layout.addWidget(widget)
        self.affix_pool_layout.addWidget(container)
        QTimer.singleShot(50, container.expand)

    def add_affix_pool(self):
        default_affix = AffixFilterModel(name=next(iter(Dataloader().affix_dict.keys())), value=None)
        new_pool = AffixFilterCountModel(count=[default_affix], min_count=1, max_count=3)
        self.config.affix_pool.append(new_pool)
        self.add_affix_pool_item(new_pool)

    def remove_selected(self):
        dialog = DeleteAffixPool(self.affix_pool_layout.count())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        to_delete = dialog.get_value()
        to_delete_list = []
        for i in range(self.affix_pool_layout.count()):
            item = self.affix_pool_layout.itemAt(i)
            if item and item.widget() is not None and item.widget().header.name in to_delete:
                to_delete_list.append((item.widget(), i))
        to_delete_list.reverse()
        for widget, index in to_delete_list:
            widget.setParent(None)
            self.config.affix_pool.pop(index)
        self.reorganize_pool()

    def reorganize_pool(self):
        for i in range(self.affix_pool_layout.count()):
            item = self.affix_pool_layout.itemAt(i)
            if item and item.widget() is not None:
                item.widget().header.set_name(f"Count {i}")

    def update_min_greater_affix(self):
        self.config.min_greater_affix_count = self.min_greater.value()

    def update_rarities(self):
        self.config.rarities = [rarity for rarity, checkbox in self.rarity_checkboxes.items() if checkbox.isChecked()]

    def update_charm_slots(self, slots: int, checked: bool):
        if not checked:
            if self.config.charm_slots == slots:
                self.config.charm_slots = 0
            return

        self.config.charm_slots = slots
        for other_slots, checkbox in self.charm_slot_checkboxes.items():
            if other_slots == slots:
                continue
            with QSignalBlocker(checkbox):
                checkbox.setChecked(False)

    def update_boosted_set(self, index: int, _current_text=None):
        self.sync_boosted_sets_from_controls()
        self.refresh_boosted_affix_controls(index)

    def update_boosted_affix(self, index: int, _current_text=None):
        self.sync_boosted_sets_from_controls()
        self.refresh_boosted_affix_controls(index)

    def update_boosted_affix_required(self, index: int, checked: bool):
        self.boosted_affix_required_checkboxes[index].setChecked(checked)
        self.sync_boosted_sets_from_controls()

    def update_boosted_affix_mode(self, index: int, _current_text=None):
        self.sync_boosted_sets_from_controls()
        self.refresh_boosted_affix_controls(index)

    def update_boosted_affix_value(self, index: int, value):
        if self.boosted_affix_modes[index].currentText() == AFFIX_PERCENT_MODE:
            try:
                percent = int(value) if value else 0
            except ValueError:
                return
            if not 0 <= percent <= 100:
                QMessageBox.warning(self, "Warning", "Min % must be between 0 and 100.")
                self.refresh_boosted_affix_controls(index)
                return

        self.sync_boosted_sets_from_controls()

    def sync_boosted_sets_from_controls(self):
        boosted_sets = []
        for index in range(BOOSTED_SET_SLOT_COUNT):
            set_name = correct_name(self.boosted_set_combos[index].currentText())
            if not set_name or set_name not in Dataloader().set_list:
                continue

            boosted_sets.append(
                BoostedSetFilterModel(
                    set=set_name,
                    affix=self.boosted_affix_from_controls(index),
                    required=self.boosted_affix_required_checkboxes[index].isChecked()
                    and self.boosted_affix_from_controls(index) is not None,
                )
            )

        self.config.boosted_set = None
        self.config.boosted_affix = None
        self.config.boosted_affix_required = False
        self.config.boosted_sets = boosted_sets

    def boosted_affix_from_controls(self, index: int) -> AffixFilterModel | None:
        current_text = self.boosted_affix_combos[index].currentText()
        if not current_text.strip():
            return None

        reverse_dict = {v: k for k, v in Dataloader().affix_dict.items()}
        affix_name = reverse_dict.get(current_text) or correct_name(current_text)
        if affix_name not in Dataloader().affix_dict:
            return None

        affix = AffixFilterModel(name=affix_name, value=None)
        value = self.boosted_affix_values[index].text()
        if self.boosted_affix_modes[index].currentText() == AFFIX_PERCENT_MODE:
            try:
                affix.min_percent_of_affix = int(value) if value else 0
            except ValueError:
                return affix
            affix.value = None
            return affix

        try:
            affix.value = float(value) if value else None
        except ValueError:
            return affix
        affix.min_percent_of_affix = 0
        return affix

    def refresh_boosted_affix_controls(self, index: int):
        set_name = correct_name(self.boosted_set_combos[index].currentText())
        affix = self.boosted_affix_from_controls(index)
        affix_selected = affix is not None
        can_require_affix = bool(set_name and set_name in Dataloader().set_list and affix_selected)

        if not can_require_affix:
            with QSignalBlocker(self.boosted_affix_required_checkboxes[index]):
                self.boosted_affix_required_checkboxes[index].setChecked(False)

        self.boosted_affix_required_checkboxes[index].setEnabled(can_require_affix)
        self.boosted_affix_modes[index].setEnabled(affix_selected)
        self.boosted_affix_values[index].setEnabled(affix_selected)

        if not affix_selected:
            with QSignalBlocker(self.boosted_affix_values[index]):
                self.boosted_affix_values[index].clear()
            return

        if self.boosted_affix_modes[index].currentText() == AFFIX_PERCENT_MODE:
            self.boosted_affix_values[index].setPlaceholderText("Percent (0-100)")
            self.boosted_affix_values[index].setValidator(QIntValidator(0, 100, self.boosted_affix_values[index]))
            display_value = "" if affix.min_percent_of_affix == 0 else str(affix.min_percent_of_affix)
        else:
            self.boosted_affix_values[index].setPlaceholderText("Value (optional)")
            self.boosted_affix_values[index].setValidator(QDoubleValidator(self.boosted_affix_values[index]))
            display_value = "" if affix.value is None else str(affix.value)

        with QSignalBlocker(self.boosted_affix_values[index]):
            self.boosted_affix_values[index].setText(display_value)


class SealCharmTab(QWidget):
    def __init__(
        self,
        filters: list[DynamicSealCharmFilterModel],
        section_name: str,
        dynamic_model: type[DynamicSealCharmFilterModel | DynamicCharmFilterModel | DynamicSealFilterModel],
        filter_model: type[SealCharmFilterModel | CharmFilterModel | SealFilterModel],
        parent=None,
    ):
        super().__init__(parent)
        self.filters = filters
        self.section_name = section_name
        self.dynamic_model = dynamic_model
        self.filter_model = filter_model
        self.loaded = False

    def load(self):
        if not self.loaded:
            self.setup_ui()
            self.loaded = True

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 20, 0, 20)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        self.toolbar = QToolBar(f"{self.section_name}Toolbar", self)
        self.toolbar.setMinimumHeight(50)
        self.toolbar.setContentsMargins(10, 10, 10, 10)
        self.toolbar.setMovable(False)

        self.rule_names = []
        for seal_charm_filter in self.filters:
            for rule_name in seal_charm_filter.root:
                if rule_name in self.rule_names:
                    QMessageBox.warning(
                        self, "Warning", f"Rule name already exists. Please rename {rule_name} in the profile file."
                    )
                    continue
                self.rule_names.append(rule_name)
                self.tab_widget.addTab(SealCharmRuleEditor(seal_charm_filter), rule_name)

        add_rule_button = QPushButton("Create Item")
        add_rule_button.clicked.connect(self.add_rule)
        remove_rule_button = QPushButton("Remove Item")
        remove_rule_button.clicked.connect(self.remove_rule)

        self.toolbar.addWidget(add_rule_button)
        self.toolbar.addWidget(remove_rule_button)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addWidget(self.tab_widget)

    def add_rule(self):
        rule_name, ok = QInputDialog.getText(self, f"Create {self.section_name} Rule", "Rule Name:")
        if not ok:
            return
        rule_name = rule_name.strip()
        if not rule_name:
            QMessageBox.warning(self, "Warning", "Rule name cannot be empty.")
            return
        if rule_name in self.rule_names:
            QMessageBox.warning(self, "Warning", "Rule name already exists.")
            return

        new_filter = self.dynamic_model(root={rule_name: self._default_filter()})
        self.filters.append(new_filter)
        self.rule_names.append(rule_name)
        self.tab_widget.addTab(SealCharmRuleEditor(new_filter), rule_name)

    def close_tab(self, index):
        self.rule_names.pop(index)
        self.tab_widget.removeTab(index)
        self.filters.pop(index)

    def remove_rule(self):
        dialog = DeleteItem(self.rule_names, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        rule_names_to_delete = dialog.get_value()
        for rule_name in rule_names_to_delete:
            index = self.rule_names.index(rule_name)
            self.rule_names.remove(rule_name)
            self.tab_widget.removeTab(index)
            self.filters.pop(index)

    def _default_filter(self) -> SealCharmFilterModel:
        return self.filter_model(
            affix_pool=[
                AffixFilterCountModel(
                    count=[AffixFilterModel(name=next(iter(Dataloader().affix_dict.keys())))], min_count=1, max_count=3
                )
            ]
        )
