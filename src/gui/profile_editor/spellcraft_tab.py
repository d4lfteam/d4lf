from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
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
    CharmFilterModel,
    DynamicCharmFilterModel,
    DynamicSealFilterModel,
    DynamicSpellcraftFilterModel,
    SealFilterModel,
    SpellcraftFilterModel,
)
from src.dataloader import Dataloader
from src.gui.models.collapsible_widget import Container
from src.gui.models.dialog import DeleteAffixPool, DeleteItem
from src.gui.profile_editor.affixes_tab import AffixPoolWidget
from src.item.data.rarity import ItemRarity

SEALS_TABNAME = "Seals"
CHARMS_TABNAME = "Charms"


class SpellcraftRuleEditor(QWidget):
    def __init__(self, dynamic_filter: DynamicSpellcraftFilterModel, parent=None):
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


class SpellcraftTab(QWidget):
    def __init__(
        self,
        filters: list[DynamicSpellcraftFilterModel],
        section_name: str,
        dynamic_model: type[DynamicSpellcraftFilterModel | DynamicCharmFilterModel | DynamicSealFilterModel],
        filter_model: type[SpellcraftFilterModel | CharmFilterModel | SealFilterModel],
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
        for spellcraft_filter in self.filters:
            for rule_name in spellcraft_filter.root:
                if rule_name in self.rule_names:
                    QMessageBox.warning(
                        self, "Warning", f"Rule name already exists. Please rename {rule_name} in the profile file."
                    )
                    continue
                self.rule_names.append(rule_name)
                self.tab_widget.addTab(SpellcraftRuleEditor(spellcraft_filter), rule_name)

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
        self.tab_widget.addTab(SpellcraftRuleEditor(new_filter), rule_name)

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

    def _default_filter(self) -> SpellcraftFilterModel:
        return self.filter_model(
            affix_pool=[
                AffixFilterCountModel(
                    count=[AffixFilterModel(name=next(iter(Dataloader().affix_dict.keys())))], min_count=1, max_count=3
                )
            ]
        )
