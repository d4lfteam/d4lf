from typing import TYPE_CHECKING, override

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.game_data import GameCatalog
from src.profiles import CharmFilterModel, DynamicCharmFilterModel, DynamicSealFilterModel, SealFilterModel
from src.profiles.charm_seal.dialogs import SetPicker
from src.profiles.editor.helpers import create_picker_row, create_readonly_line_edit
from src.profiles.editor.pickers import RarityPicker, rarity_summary
from src.profiles.pool_controls import AffixPoolSection, GreaterAffixControls, UniqueAspectSection

if TYPE_CHECKING:
    from pydantic import RootModel


def _set_summary(sets: list[str]) -> str:
    if not sets:
        return "No sets selected"
    return ", ".join(sets)


class BaseGroupEditor[ConfigT: CharmFilterModel | SealFilterModel](QWidget):
    """Shared base editor class for single-named filters (Charms and Seals)."""

    def __init__(
        self, dynamic_filter: RootModel[dict[str, ConfigT]], is_charm: bool, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.type_prefix = "charm" if is_charm else "seal"
        if len(dynamic_filter.root) != 1:
            msg = "BaseGroupEditor requires a single-key dynamic filter model."
            raise ValueError(msg)
        self.item_name, self.config = next(iter(dynamic_filter.root.items()))
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

        general_form = QFormLayout()
        self.rarity_line_edit = create_readonly_line_edit()
        self.refresh_rarity_summary()
        general_form.addRow("Rarities:", create_picker_row(self.rarity_line_edit, self.edit_rarities))
        self.add_custom_general_fields(general_form)
        self.greater_controls = GreaterAffixControls(self.config, f"{self.type_prefix}_{self.item_name}")
        general_form.addRow("Min Greater Affixes:", self.greater_controls)

        catalog = GameCatalog()
        affix_dict = catalog.charm_affix_dict if is_charm else catalog.seal_affix_dict
        self.unique_aspects = UniqueAspectSection(self.config, aspect_prefix=f"{self.type_prefix}_of")
        self.affix_pools = AffixPoolSection("Affix Pool", self.config.affix_pool, next(iter(affix_dict), ""))
        self.affix_pools.pools_removed.connect(self.greater_controls.refresh)

        pool_btn_layout = QHBoxLayout()
        add_affix_pool_btn = QPushButton("Add Affix Pool")
        add_affix_pool_btn.clicked.connect(self.affix_pools.add_pool)
        remove_affix_pool_btn = QPushButton("Remove Affix Pool")
        remove_affix_pool_btn.clicked.connect(self.affix_pools.remove_pools)
        pool_btn_layout.addWidget(add_affix_pool_btn)
        pool_btn_layout.addWidget(remove_affix_pool_btn)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.addLayout(general_form)
        content_layout.addWidget(self.unique_aspects)
        content_layout.addWidget(self.affix_pools)
        content_layout.addLayout(pool_btn_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(content_widget)
        QVBoxLayout(self).addWidget(scroll_area)

        QTimer.singleShot(100, self.affix_pools.expand)

    def add_custom_general_fields(self, general_form: QFormLayout) -> None:
        """Hook for subclasses to add their own general fields."""

    def refresh_greater_count(self) -> None:
        """Called by child ``AffixWidget``s when a Greater checkbox changes."""
        self.greater_controls.refresh()

    def edit_rarities(self) -> None:
        dialog = RarityPicker(self, self.config.rarities)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config.rarities = dialog.get_selected_rarities()
            self.refresh_rarity_summary()

    def refresh_rarity_summary(self) -> None:
        self.rarity_line_edit.setText(rarity_summary(self.config.rarities))


class CharmGroupEditor(BaseGroupEditor[CharmFilterModel]):
    """Editor widget for a single named charm filter."""

    def __init__(self, dynamic_filter: DynamicCharmFilterModel, parent: QWidget | None = None) -> None:
        super().__init__(dynamic_filter, is_charm=True, parent=parent)

    @override
    def add_custom_general_fields(self, general_form: QFormLayout) -> None:
        """Add charm-specific set selection row."""
        self.set_line_edit = create_readonly_line_edit()
        self.refresh_set_summary()
        general_form.addRow("Sets:", create_picker_row(self.set_line_edit, self.edit_sets))

    def edit_sets(self) -> None:
        if self.config.unique_aspect:
            QMessageBox.warning(self, "Warning", "Cannot select sets when unique aspects are defined.")
            return
        dialog = SetPicker(parent=self, selected_sets=self.config.set)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config.set = dialog.get_selected_sets()
            self.refresh_set_summary()

    def refresh_set_summary(self) -> None:
        self.set_line_edit.setText(_set_summary(self.config.set))


class SealGroupEditor(BaseGroupEditor[SealFilterModel]):
    """Editor widget for a single named seal filter."""

    def __init__(self, dynamic_filter: DynamicSealFilterModel, parent: QWidget | None = None) -> None:
        super().__init__(dynamic_filter, is_charm=False, parent=parent)
