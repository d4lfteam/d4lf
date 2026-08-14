from typing import TYPE_CHECKING, cast, override

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.settings import CATEGORY_KEY, CATEGORY_ORDER, HIDE_FROM_GUI_KEY, IS_HOTKEY_KEY, SettingsCategory
from src.settings.reset import ConfigResetMixin
from src.settings.store import SettingsStore
from src.settings.tab_mixin import ConfigTabMixin

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel

    from src.settings.types import SettingValue

CONFIG_TABNAME = "config"


class ConfigTab(ConfigTabMixin, ConfigResetMixin, QWidget):
    def __init__(self, theme_changed_callback: Callable[[], None] | None = None) -> None:
        self._initializing = True
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.theme_changed_callback = theme_changed_callback
        self._settings_store = SettingsStore()
        self.model_to_parameter_value_map = {}
        self._all_rows = []
        self._group_boxes = {}  # Store group boxes to move them during search
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        # Search Bar
        search_container = QWidget()
        search_hbox = QHBoxLayout(search_container)
        search_hbox.setContentsMargins(10, 0, 10, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search settings...")
        self.search_input.textChanged.connect(self._filter_settings)
        search_hbox.addWidget(self.search_input)
        layout.addWidget(search_container)
        # Main Content: Navigation List (Left) and Stacked Widget (Right)
        main_content = QWidget()
        content_hbox = QHBoxLayout(main_content)
        content_hbox.setContentsMargins(0, 0, 0, 0)
        content_hbox.setSpacing(2)
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("nav-list")
        self.nav_list.setSpacing(0)
        self.nav_list.setUniformItemSizes(True)
        self.nav_list.setFixedWidth(160)
        self.stacked_widget = QStackedWidget()
        self.nav_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        content_hbox.addWidget(self.nav_list)
        content_hbox.addWidget(self.stacked_widget, stretch=1)
        layout.addWidget(main_content, stretch=1)
        # Special Search Results Page
        self.search_results_page = QScrollArea()
        self.search_results_page.setWidgetResizable(True)
        self.search_results_container = QWidget()
        self.search_results_layout = QVBoxLayout(self.search_results_container)
        self.search_results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.search_results_page.setWidget(self.search_results_container)
        # Build Subsections
        self._build_sections()
        # Bottom Action Buttons
        action_bar = QWidget()
        action_bar.setObjectName("action-bar")
        action_hbox = QHBoxLayout(action_bar)
        action_hbox.setContentsMargins(10, 10, 10, 10)
        action_hbox.addWidget(self._setup_reset_button())
        action_hbox.addStretch()
        layout.addWidget(action_bar)
        self.setLayout(layout)
        QTimer.singleShot(0, self._finish_init)

    def _finish_init(self) -> None:
        self._initializing = False

    def _build_sections(self) -> None:
        models = self._settings_store.models_with_sections()
        # 1. Bucket settings by category using model metadata
        categories_map = {}
        for model, section in models:
            meta_all = model.model_json_schema()["properties"]
            for key, val in model:
                if key == "profiles":
                    continue
                meta = meta_all.get(key, {})
                if meta.get(HIDE_FROM_GUI_KEY):
                    continue
                cat = meta.get(CATEGORY_KEY)
                if not cat:
                    # Compatibility/Fallback for hotkeys and advanced options that might not have a category set
                    if meta.get(IS_HOTKEY_KEY) == "True":
                        cat = SettingsCategory.HOTKEYS
                    elif section == "advanced_options":
                        cat = SettingsCategory.ADVANCED
                    else:
                        continue
                categories_map.setdefault(cat, []).append((model, section, key, val))
        # 2. Create pages and group boxes in the designated order
        for cat_name in CATEGORY_ORDER:
            settings_list = categories_map.get(cat_name)
            if not settings_list:
                continue
            page = self._create_page(cat_name)
            layout = page.findChild(QVBoxLayout)
            # Determine a nice title for the group box
            if cat_name == SettingsCategory.HOTKEYS:
                gb_title = "Key Bindings"
            elif cat_name == SettingsCategory.ADVANCED:
                gb_title = "Technical Settings"
            else:
                gb_title = str(cat_name).replace("&", "&&")
            gb = QGroupBox(gb_title)
            grid = QGridLayout(gb)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(2, 1)
            for model, section, key, val in settings_list:
                self._add_setting_row(grid, grid.rowCount(), model, section, key, val)
            layout.addWidget(gb)
            self._group_boxes[cat_name] = gb

    def _create_page(self, name: str) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(container)
        self.nav_list.addItem(name)
        self.stacked_widget.addWidget(scroll)
        return container

    @override
    def _add_setting_row(
        self, grid: QGridLayout, row: int, model: BaseModel, section: str, key: str, val: SettingValue
    ) -> None:
        meta = model.model_json_schema()["properties"].get(key, {})
        if meta.get(HIDE_FROM_GUI_KEY):
            return
        human_label = meta.get("title") or key.replace("_", " ").title()
        label_container = QWidget()
        label_vbox = QVBoxLayout(label_container)
        label_vbox.setContentsMargins(0, 0, 10, 0)
        label_vbox.setSpacing(2)
        title_lbl = QLabel(human_label)
        title_lbl.setObjectName("setting-title")
        title_lbl.setWordWrap(True)
        desc_lbl = QLabel(meta.get("description", ""))
        desc_lbl.setObjectName("description-label")
        desc_lbl.setWordWrap(True)
        label_vbox.addWidget(title_lbl)
        label_vbox.addWidget(desc_lbl)
        control = self._generate_parameter_value_widget(model, section, key, val, meta.get(IS_HOTKEY_KEY))
        self.model_to_parameter_value_map[f"{section}.{key}"] = control
        grid.addWidget(label_container, row, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(control, row, 2, Qt.AlignmentFlag.AlignTop)
        self._all_rows.append((
            human_label,
            meta.get("description", ""),
            label_container,
            control,
            cast("QGroupBox", grid.parentWidget()),
        ))
