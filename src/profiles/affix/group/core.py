from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.game_data import MAX_POWER, GameCatalog, ItemType, is_armor, is_jewelry, is_weapon
from src.profiles.affix.helpers import _item_type_summary
from src.profiles.affix.picker import ItemTypePicker
from src.profiles.editor.dialogs import IgnoreScrollWheelSpinBox
from src.profiles.editor.helpers import create_picker_row, create_readonly_line_edit
from src.profiles.editor.pickers import RarityPicker, rarity_summary
from src.profiles.pool_controls import AffixPoolSection, GreaterAffixControls, UniqueAspectSection

if TYPE_CHECKING:
    from src.profiles import DynamicItemFilterModel


class AffixGroupEditor(QWidget):
    def __init__(self, dynamic_filter: DynamicItemFilterModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item_name, self.config = next(iter(dynamic_filter.root.items()))
        self.item_types = [
            item for item in ItemType.__members__.values() if is_armor(item) or is_jewelry(item) or is_weapon(item)
        ]
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.setup_ui()

    def setup_ui(self) -> None:
        general_form = QFormLayout()

        self.item_type_line_edit = create_readonly_line_edit()
        self.refresh_item_type_summary()
        general_form.addRow("Item Types:", create_picker_row(self.item_type_line_edit, self.edit_item_types))

        self.rarity_line_edit = create_readonly_line_edit()
        self.refresh_rarity_summary()
        general_form.addRow("Rarities:", create_picker_row(self.rarity_line_edit, self.edit_rarities))

        self.min_power = IgnoreScrollWheelSpinBox()
        self.min_power.setMaximum(MAX_POWER)
        self.min_power.setValue(self.config.min_power)
        self.min_power.setMaximumWidth(150)
        self.min_power.valueChanged.connect(self.update_min_power)
        general_form.addRow("Minimum Power:", self.min_power)

        self.greater_controls = GreaterAffixControls(self.config, f"affix_{self.item_name}")
        general_form.addRow("Min Greater Affixes:", self.greater_controls)

        default_affix = next(iter(GameCatalog().affix_dict), "")
        self.unique_aspects = UniqueAspectSection(self.config)
        self.affix_pools = AffixPoolSection("Affix Pool", self.config.affix_pool, default_affix)
        self.affix_pools.pools_removed.connect(self.greater_controls.refresh)
        self.inherent_pools = AffixPoolSection("Inherent Pool", self.config.inherent_pool, default_affix, inherent=True)

        pool_btn_layout = QHBoxLayout()
        for text, handler in (
            ("Add Affix Pool", self.affix_pools.add_pool),
            ("Add Inherent Pool", self.inherent_pools.add_pool),
            ("Remove Affix Pool", self.affix_pools.remove_pools),
            ("Remove Inherent Pool", self.inherent_pools.remove_pools),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            pool_btn_layout.addWidget(button)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.addLayout(general_form)
        content_layout.addWidget(self.unique_aspects)
        content_layout.addWidget(self.affix_pools)
        content_layout.addWidget(self.inherent_pools)
        content_layout.addLayout(pool_btn_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(content_widget)
        QVBoxLayout(self).addWidget(scroll_area)

    def refresh_greater_count(self) -> None:
        """Called by child ``AffixWidget``s when a Greater checkbox changes."""
        self.greater_controls.refresh()

    def refresh_item_type_summary(self) -> None:
        self.item_type_line_edit.setText(_item_type_summary(self.config.item_type))

    def edit_item_types(self) -> None:
        item_type_picker = ItemTypePicker(self, self.item_types, self.config.item_type)
        if item_type_picker.exec() == QDialog.DialogCode.Accepted:
            self.config.item_type = item_type_picker.get_selected_item_types()
            self.refresh_item_type_summary()

    def refresh_rarity_summary(self) -> None:
        self.rarity_line_edit.setText(rarity_summary(self.config.rarities))

    def edit_rarities(self) -> None:
        rarity_picker = RarityPicker(self, self.config.rarities)
        if rarity_picker.exec() == QDialog.DialogCode.Accepted:
            self.config.rarities = rarity_picker.get_selected_rarities()
            self.refresh_rarity_summary()

    def update_min_power(self) -> None:
        self.config.min_power = self.min_power.value()
