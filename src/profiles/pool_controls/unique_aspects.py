from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout

from src.game_data import GameCatalog
from src.profiles import AspectUniqueFilterModel, CharmFilterModel, ItemFilterModel, SealFilterModel
from src.profiles.affix.unique_aspect import UNIQUE_ASPECTS_TITLE, UniqueAspectWidget
from src.profiles.editor.container import Container
from src.profiles.editor.helpers import refresh_widget_style


def _title(config: ItemFilterModel | CharmFilterModel | SealFilterModel) -> str:
    aspect_names = ", ".join(unique_aspect.name for unique_aspect in config.unique_aspect) or "None"
    return f"{UNIQUE_ASPECTS_TITLE} - {aspect_names}"


def _header_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("affixHeaderLabel", True)  # ruff:ignore[FBT003]
    refresh_widget_style(label)
    return label


class UniqueAspectSection(Container):
    """Collapsible list editing ``config.unique_aspect``, limited to aspects starting with ``aspect_prefix``."""

    def __init__(self, config: ItemFilterModel | CharmFilterModel | SealFilterModel, aspect_prefix: str = "") -> None:
        super().__init__(_title(config))
        self._config = config
        self._allowed_aspects = sorted(
            name for name in GameCatalog().aspect_unique_dict if name.startswith(aspect_prefix)
        )

        self.aspect_list = QListWidget()
        self.aspect_list.setFixedHeight(180)
        self.aspect_list.setAlternatingRowColors(True)
        self.aspect_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.aspect_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Unique Aspect")
        add_btn.clicked.connect(self.add_aspect)
        remove_btn = QPushButton("Remove Unique Aspect")
        remove_btn.clicked.connect(self.remove_selected_aspects)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)

        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_layout.addSpacing(25)
        title_layout.addWidget(_header_label("Aspect"))
        title_layout.addSpacing(440)
        title_layout.addWidget(_header_label("Mode"))
        title_layout.addSpacing(85)
        title_layout.addWidget(_header_label("Threshold"))

        layout = QVBoxLayout(self.content_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addLayout(btn_layout)
        layout.addLayout(title_layout)
        layout.addWidget(self.aspect_list)

        self.first_expansion.connect(self._load_aspects)

    def add_aspect(self) -> None:
        if isinstance(self._config, CharmFilterModel) and self._config.set:
            QMessageBox.warning(self, "Warning", "Cannot add unique aspects when sets are selected.")
            return
        self.expand()
        existing_names = {unique_aspect.name for unique_aspect in self._config.unique_aspect}
        aspect_name = next((name for name in self._allowed_aspects if name not in existing_names), None)
        if aspect_name is None:
            QMessageBox.information(self, "Info", "All unique aspects have already been added.")
            return
        unique_aspect = AspectUniqueFilterModel(name=aspect_name, value=None)
        self._config.unique_aspect.append(unique_aspect)
        self._add_item(unique_aspect)
        self.refresh_unique_aspects_title()

    def remove_selected_aspects(self) -> None:
        rows = sorted((self.aspect_list.row(item) for item in self.aspect_list.selectedItems()), reverse=True)
        for row in rows:
            self.aspect_list.takeItem(row)
            del self._config.unique_aspect[row]
        self.refresh_unique_aspects_title()

    def refresh_unique_aspects_title(self) -> None:
        """Called by child ``UniqueAspectWidget``s when an aspect is renamed."""
        self.header.set_name(_title(self._config))

    def _load_aspects(self) -> None:
        for unique_aspect in self._config.unique_aspect:
            self._add_item(unique_aspect)

    def _add_item(self, unique_aspect: AspectUniqueFilterModel) -> None:
        item = QListWidgetItem()
        widget = UniqueAspectWidget(unique_aspect, allowed_aspects=self._allowed_aspects)
        item_size = widget.sizeHint()
        item_size.setWidth(850)
        item.setSizeHint(item_size)
        self.aspect_list.addItem(item)
        self.aspect_list.setItemWidget(item, widget)
