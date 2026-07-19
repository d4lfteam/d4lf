from typing import Any, cast

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.item import Dataloader
from src.profiles import AffixFilterCountModel, AffixFilterModel, AspectUniqueFilterModel
from src.profiles.affix.dialogs import DeleteAffixPool
from src.profiles.affix.pool import AffixPoolWidget
from src.profiles.affix.unique_aspect import UniqueAspectWidget
from src.profiles.editor import Container, refresh_widget_style

AFFIXES_TABNAME = "Affixes"
AFFIX_VALUE_MODE = "Value"
AFFIX_PERCENT_MODE = "Min %"
UNIQUE_ASPECTS_TITLE = "Unique Aspects"


class _AffixGroupPoolsMixin:
    def create_unique_aspect_container(self: Any):
        self.unique_aspect_container = Container(self._unique_aspects_title())
        self.unique_aspect_layout = QVBoxLayout(self.unique_aspect_container.content_widget)
        self.unique_aspect_container.first_expansion.connect(self.init_unique_aspects)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        aspect_label = QLabel("Aspect")
        aspect_label.setProperty("affixHeaderLabel", True)  # ruff:ignore[boolean-positional-value-in-call]
        refresh_widget_style(aspect_label)

        mode_label = QLabel("Mode")
        mode_label.setProperty("affixHeaderLabel", True)  # ruff:ignore[boolean-positional-value-in-call]
        refresh_widget_style(mode_label)

        value_label = QLabel("Threshold")
        value_label.setProperty("affixHeaderLabel", True)  # ruff:ignore[boolean-positional-value-in-call]
        refresh_widget_style(value_label)

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

    def _unique_aspects_title(self: Any):
        aspect_names = ", ".join(unique_aspect.name for unique_aspect in self.config.unique_aspect) or "None"
        return f"{UNIQUE_ASPECTS_TITLE} - {aspect_names}"

    def refresh_unique_aspects_title(self: Any):
        self.unique_aspect_container.header.set_name(self._unique_aspects_title())

    def init_unique_aspects(self: Any):
        for unique_aspect in self.config.unique_aspect:
            self.add_unique_aspect_item(unique_aspect)

    def add_unique_aspect_item(self: Any, unique_aspect: AspectUniqueFilterModel):
        item = QListWidgetItem()
        widget = UniqueAspectWidget(unique_aspect)
        item_size = widget.sizeHint()
        item_size.setWidth(850)
        item.setSizeHint(item_size)
        self.unique_aspect_list.addItem(item)
        self.unique_aspect_list.setItemWidget(item, widget)

    def add_unique_aspect(self: Any):
        existing_names = {unique_aspect.name for unique_aspect in self.config.unique_aspect}
        for aspect_name in Dataloader().aspect_unique_dict:
            if aspect_name in existing_names:
                continue
            new_unique_aspect = AspectUniqueFilterModel(name=aspect_name, value=None)
            self.config.unique_aspect.append(new_unique_aspect)
            self.add_unique_aspect_item(new_unique_aspect)
            self.refresh_unique_aspects_title()
            return
        QMessageBox.information(cast("QWidget", self), "Info", "All unique aspects have already been added.")

    def remove_selected_unique_aspects(self: Any):
        selected_rows = sorted(
            (self.unique_aspect_list.row(item) for item in self.unique_aspect_list.selectedItems()), reverse=True
        )
        for row in selected_rows:
            self.unique_aspect_list.takeItem(row)
            del self.config.unique_aspect[row]
        self.refresh_unique_aspects_title()

    def init_affix_pool(self: Any):
        """Initialize affix pool content on first expansion."""
        for pool in self.config.affix_pool:
            self.add_affix_pool_item(pool)
        QTimer.singleShot(50, self.update_greater_count_label)

    def init_inherent_pool(self: Any):
        """Initialize inherent pool content on first expansion."""
        for pool in self.config.inherent_pool:
            self.add_affix_pool_item(pool, inherent=True)
        QTimer.singleShot(50, self.update_greater_count_label)

    def add_affix_pool_item(self: Any, pool: AffixFilterCountModel, inherent: bool = False):
        if inherent:
            nb_count = self.inherent_pool_layout.count()
            container = Container(f"Count {nb_count}", color_background=True)
            container_layout = QVBoxLayout(container.content_widget)
            widget = AffixPoolWidget(pool, self)
            container_layout.addWidget(widget)
            self.inherent_pool_layout.addWidget(container)
            QTimer.singleShot(50, container.expand)
        else:
            nb_count = self.affix_pool_layout.count()
            container = Container(f"Count {nb_count}", color_background=True)
            container_layout = QVBoxLayout(container.content_widget)
            widget = AffixPoolWidget(pool, self)
            container_layout.addWidget(widget)
            self.affix_pool_layout.addWidget(container)
            QTimer.singleShot(50, container.expand)

    def add_affix_pool(self: Any):
        default_affix = AffixFilterModel(
            name=next(iter(Dataloader().affix_dict.keys()), ""),  # First valid affix name
            value=None,
        )

        new_pool = AffixFilterCountModel(count=[default_affix], min_count=1, max_count=3)
        self.config.affix_pool.append(new_pool)
        self.add_affix_pool_item(new_pool)

    def add_inherent_pool(self: Any):
        default_affix = AffixFilterModel(
            name=next(iter(Dataloader().affix_dict.keys()), ""),  # First valid affix name
            value=None,
        )

        new_pool = AffixFilterCountModel(count=[default_affix], min_count=1, max_count=3)
        self.config.inherent_pool.append(new_pool)
        self.add_affix_pool_item(new_pool, inherent=True)

    def remove_selected(self: Any, layout_widget: QVBoxLayout, inherent: bool = False):
        nb_pool = layout_widget.count()
        dialog = DeleteAffixPool(nb_pool, inherent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            to_delete = dialog.get_value()
            to_delete_list = []
            for i in range(layout_widget.count()):
                item = layout_widget.itemAt(i)
                if item is None:
                    continue
                widget = item.widget()
                if isinstance(widget, Container) and widget.header.name in to_delete:
                    to_delete_list.append((widget, i))
            to_delete_list.reverse()
            for widget, index in to_delete_list:
                widget.setParent(None)
                if inherent:
                    self.config.inherent_pool.pop(index)
                else:
                    self.config.affix_pool.pop(index)
            self.reorganize_pool(layout_widget)

    def reorganize_pool(self: Any, layout_widget: QVBoxLayout):
        for i in range(layout_widget.count()):
            item = layout_widget.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if isinstance(widget, Container):
                widget.header.set_name(f"Count {i}")
