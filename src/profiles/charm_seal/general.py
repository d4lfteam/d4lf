from typing import Any, cast

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.game_data import GameCatalog
from src.profiles import AffixFilterCountModel, AspectUniqueFilterModel, CharmFilterModel
from src.profiles.affix import UNIQUE_ASPECTS_TITLE, AffixPoolWidget, UniqueAspectWidget
from src.profiles.editor.container import Container
from src.profiles.editor.helpers import create_auto_sync_checkbox, create_readonly_line_edit, refresh_widget_style

CHARMS_TABNAME = "Charms"
SEALS_TABNAME = "Seals"


def _set_summary(sets: list[str]) -> str:
    if not sets:
        return "No sets selected"
    return ", ".join(sets)


class _CharmSealGeneralMixin:
    def add_rarity_row(self: Any, general_form: QFormLayout):
        """Add the rarity picker row to the form."""
        self.rarity_line_edit = create_readonly_line_edit()
        self.refresh_rarity_summary()

        rarity_layout = QHBoxLayout()
        rarity_layout.addWidget(self.rarity_line_edit)
        edit_rarities_btn = QPushButton("...")
        edit_rarities_btn.setMaximumWidth(40)
        edit_rarities_btn.clicked.connect(self.edit_rarities)
        rarity_layout.addWidget(edit_rarities_btn)
        rarity_layout.addStretch()
        general_form.addRow("Rarities:", rarity_layout)

    def add_min_greater_row(self: Any, general_form: QFormLayout):
        """Add the Min Greater Affixes and Auto Sync controls to the form."""
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

        self.auto_sync_checkbox = create_auto_sync_checkbox()
        self.auto_sync_checkbox.setChecked(
            self.settings.value(f"auto_sync_ga_{self.type_prefix}_{self.item_name}", defaultValue=False, type=bool)
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

    def add_affix_pool_section(self: Any):
        """Add the affix pool section to the layout."""
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

    def add_custom_general_fields(self: Any, general_form: QFormLayout) -> None:
        """Stub method for subclasses to add their unique general fields."""

    # --- Unique Aspects ---

    def _unique_aspects_title(self: Any) -> str:
        aspect_names = ", ".join(unique_aspect.name for unique_aspect in self.config.unique_aspect) or "None"
        return f"{UNIQUE_ASPECTS_TITLE} - {aspect_names}"

    def refresh_unique_aspects_title(self: Any):
        self.unique_aspect_container.header.set_name(self._unique_aspects_title())

    def create_unique_aspect_container(self: Any):
        container = Container(UNIQUE_ASPECTS_TITLE)
        layout = QVBoxLayout(container.content_widget)

        self.unique_aspect_list = QListWidget()
        self.unique_aspect_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.unique_aspect_list.setMinimumHeight(150)
        self.init_unique_aspects()

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Aspect")
        add_btn.clicked.connect(self.add_unique_aspect)
        remove_btn = QPushButton("Remove Aspect")
        remove_btn.clicked.connect(self.remove_unique_aspect)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)

        layout.addWidget(self.unique_aspect_list)
        layout.addLayout(btn_layout)

        self.unique_aspect_container = container
        self.content_layout.addWidget(container)

    def init_unique_aspects(self: Any):
        for unique_aspect in self.config.unique_aspect:
            self.add_unique_aspect_item(unique_aspect)

    def add_unique_aspect_item(self: Any, unique_aspect: AspectUniqueFilterModel):
        item = QListWidgetItem()
        allowed = sorted([k for k in GameCatalog().aspect_unique_dict if k.startswith(f"{self.type_prefix}_of")])
        widget = UniqueAspectWidget(unique_aspect, allowed_aspects=allowed, parent=self)
        item_size = widget.sizeHint()
        item_size.setWidth(850)
        item.setSizeHint(item_size)
        self.unique_aspect_list.addItem(item)
        self.unique_aspect_list.setItemWidget(item, widget)

    def add_unique_aspect(self: Any):
        if self.is_charm:
            if not isinstance(self.config, CharmFilterModel):
                msg = "Charm editors require a charm filter model."
                raise TypeError(msg)
            if self.config.set:
                QMessageBox.warning(
                    cast("QWidget", self), "Warning", "Cannot add unique aspects when sets are selected."
                )
                return
        existing_names = {unique_aspect.name for unique_aspect in self.config.unique_aspect}
        allowed = [k for k in GameCatalog().aspect_unique_dict if k.startswith(f"{self.type_prefix}_of")]
        for aspect_name in allowed:
            if aspect_name in existing_names:
                continue
            new_unique_aspect = AspectUniqueFilterModel(name=aspect_name, value=None)
            self.config.unique_aspect.append(new_unique_aspect)
            self.add_unique_aspect_item(new_unique_aspect)
            break
        self.refresh_unique_aspects_title()

    def remove_unique_aspect(self: Any):
        row = self.unique_aspect_list.currentRow()
        if row != -1:
            self.unique_aspect_list.takeItem(row)
            del self.config.unique_aspect[row]
        self.refresh_unique_aspects_title()

    # --- Affix Pool ---

    def init_affix_pool(self: Any):
        """Initialize affix pool content on first expansion."""
        for pool in self.config.affix_pool:
            self.add_affix_pool_item(pool)
        QTimer.singleShot(50, self.update_greater_count_label)

    def add_affix_pool_item(self: Any, pool: AffixFilterCountModel):
        nb_count = self.affix_pool_layout.count()
        container = Container(f"Count {nb_count}", color_background=True)
        container_layout = QVBoxLayout(container.content_widget)
        widget = AffixPoolWidget(pool, self)
        container_layout.addWidget(widget)
        self.affix_pool_layout.addWidget(container)
        QTimer.singleShot(50, container.expand)
