from typing import TYPE_CHECKING

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.game_data import MAX_POWER, ItemType, is_armor, is_jewelry, is_weapon
from src.profiles.affix.group.controls import _AffixGroupControlsMixin
from src.profiles.affix.group.pools import _AffixGroupPoolsMixin
from src.profiles.editor.container import Container
from src.profiles.editor.dialogs import IgnoreScrollWheelSpinBox
from src.profiles.editor.helpers import refresh_widget_style

if TYPE_CHECKING:
    from src.profiles import DynamicItemFilterModel, ItemFilterModel

AFFIXES_TABNAME = "Affixes"
AFFIX_VALUE_MODE = "Value"
AFFIX_PERCENT_MODE = "Min %"
UNIQUE_ASPECTS_TITLE = "Unique Aspects"


class AffixGroupEditor(_AffixGroupPoolsMixin, _AffixGroupControlsMixin, QWidget):
    config: ItemFilterModel
    item_type_line_edit: QLineEdit
    item_types: list[ItemType]
    rarity_line_edit: QLineEdit
    min_power: QSpinBox
    min_greater: QSpinBox
    auto_sync_checkbox: QCheckBox
    settings: QSettings
    item_name: str
    affix_pool_container: Container
    inherent_pool_container: Container
    greater_count_label: QLabel
    affix_pool_layout: QVBoxLayout
    inherent_pool_layout: QVBoxLayout
    unique_aspect_container: Container
    unique_aspect_layout: QVBoxLayout
    unique_aspect_list: QListWidget

    def __init__(self, dynamic_filter: DynamicItemFilterModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = QSettings("d4lf", "profile_editor")
        for item_name, config in dynamic_filter.root.items():
            self.item_name = item_name
            self.config = config

        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.setup_ui()

    def setup_ui(self) -> None:
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
        self.item_type_line_edit = QLineEdit()
        self.item_type_line_edit.setReadOnly(True)
        self.item_type_line_edit.setMinimumWidth(360)
        self.item_type_line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.refresh_item_type_summary()

        item_type_layout = QHBoxLayout()
        item_type_layout.addWidget(self.item_type_line_edit)
        edit_item_types_btn = QPushButton("...")
        edit_item_types_btn.setMaximumWidth(40)
        edit_item_types_btn.clicked.connect(self.edit_item_types)
        item_type_layout.addWidget(edit_item_types_btn)
        item_type_layout.addStretch()
        general_form.addRow("Item Types:", item_type_layout)

        self.rarity_line_edit = QLineEdit()
        self.rarity_line_edit.setReadOnly(True)
        self.rarity_line_edit.setMinimumWidth(360)
        self.rarity_line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.refresh_rarity_summary()

        rarity_layout = QHBoxLayout()
        rarity_layout.addWidget(self.rarity_line_edit)
        edit_rarities_btn = QPushButton("...")
        edit_rarities_btn.setMaximumWidth(40)
        edit_rarities_btn.clicked.connect(self.edit_rarities)
        rarity_layout.addWidget(edit_rarities_btn)
        rarity_layout.addStretch()
        general_form.addRow("Rarities:", rarity_layout)

        self.min_power = IgnoreScrollWheelSpinBox()
        self.min_power.setMaximum(MAX_POWER)
        self.min_power.setValue(self.config.min_power)
        self.min_power.setMaximumWidth(150)
        self.min_power.valueChanged.connect(self.update_min_power)
        general_form.addRow("Minimum Power:", self.min_power)

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

        self.auto_sync_checkbox = QCheckBox("Auto Sync")
        self.auto_sync_checkbox.setToolTip(
            "When checked: Min Greater Affixes automatically matches the number of affixes marked as 'want greater'\n"
            "When unchecked: You can manually set Min Greater Affixes to any value"
        )
        self.auto_sync_checkbox.setChecked(
            self.settings.value(f"auto_sync_ga_{self.item_name}", defaultValue=False, type=bool)
        )
        self.auto_sync_checkbox.stateChanged.connect(self.toggle_auto_sync)

        self.greater_count_label = QLabel()
        self.greater_count_label.setProperty("greaterCountLabel", True)  # ruff:ignore[boolean-positional-value-in-call]
        refresh_widget_style(self.greater_count_label)
        self.update_greater_count_label()

        min_greater_layout.addWidget(self.min_greater)
        min_greater_layout.addWidget(self.auto_sync_checkbox)
        min_greater_layout.addWidget(self.greater_count_label)
        min_greater_layout.addStretch()

        self.min_greater.setEnabled(not self.auto_sync_checkbox.isChecked())

        if self.auto_sync_checkbox.isChecked():
            self.min_greater.setProperty("autoSyncSpin", True)  # ruff:ignore[boolean-positional-value-in-call]
            refresh_widget_style(self.min_greater)

        general_form.addRow("Min Greater Affixes:", min_greater_layout)

        self.content_layout.addLayout(general_form)
        self.create_unique_aspect_container()

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
        self.affix_pool_layout = QVBoxLayout(self.affix_pool_container.content_widget)
        self.affix_pool_container.first_expansion.connect(self.init_affix_pool)

        self.inherent_pool_container = Container("Inherent Pool")
        self.inherent_pool_layout = QVBoxLayout(self.inherent_pool_container.content_widget)
        self.inherent_pool_container.first_expansion.connect(self.init_inherent_pool)

        self.content_layout.addWidget(self.affix_pool_container)
        self.content_layout.addWidget(self.inherent_pool_container)
        self.content_layout.addLayout(pool_btn_layout)

        scroll_area.setWidget(content_widget)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)
