from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.settings import CATEGORY_KEY, CATEGORY_ORDER, HIDE_FROM_GUI_KEY, IS_HOTKEY_KEY, GeneralModel, SettingsCategory
from src.settings.controls import create_control, prompt_restart, reset_control
from src.settings.store import SettingsStore

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel

    from src.settings.types import SettingValue

FILTER_KEYS = {"filter_equipment", "filter_sigils", "filter_tributes", "filter_seals", "filter_charms"}
THEME_KEYS = {"theme", "colorblind_mode"}


@dataclass(frozen=True)
class SettingRow:
    section: str
    key: str
    title: str
    description: str
    label: QWidget
    control: QWidget
    group: QGroupBox

    def matches(self, query: str) -> bool:
        return query in self.title.lower() or query in self.description.lower()

    def set_visible(self, visible: bool) -> None:
        self.label.setVisible(visible)
        self.control.setVisible(visible)


class ConfigTab(QWidget):
    def __init__(self, theme_changed_callback: Callable[[], None] | None = None) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.theme_changed_callback = theme_changed_callback
        self._settings_store = SettingsStore()
        self.rows: dict[tuple[str, str], SettingRow] = {}
        self._group_boxes: dict[str, QGroupBox] = {}  # moved into the search page while searching
        self._pages: dict[str, QVBoxLayout] = {}
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
        reset_button = QPushButton("Reset to defaults")
        reset_button.clicked.connect(self.reset_button_click)
        action_hbox.addWidget(reset_button)
        action_hbox.addStretch()
        layout.addWidget(action_bar)
        self.setLayout(layout)

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
            layout = self._create_page(cat_name)
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
                self._add_setting_row(grid, gb, model, section, key, val)
            layout.addWidget(gb)
            self._group_boxes[cat_name] = gb

    def _create_page(self, name: str) -> QVBoxLayout:
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
        self._pages[name] = layout
        return layout

    def _add_setting_row(
        self, grid: QGridLayout, group: QGroupBox, model: BaseModel, section: str, key: str, val: SettingValue
    ) -> None:
        meta = model.model_json_schema()["properties"].get(key, {})
        title = meta.get("title") or key.replace("_", " ").title()
        description = meta.get("description", "")
        label_container = QWidget()
        label_vbox = QVBoxLayout(label_container)
        label_vbox.setContentsMargins(0, 0, 10, 0)
        label_vbox.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("setting-title")
        title_lbl.setWordWrap(True)
        desc_lbl = QLabel(description)
        desc_lbl.setObjectName("description-label")
        desc_lbl.setWordWrap(True)
        label_vbox.addWidget(title_lbl)
        label_vbox.addWidget(desc_lbl)
        control = create_control(model, section, key, val, bool(meta.get(IS_HOTKEY_KEY)), self.save)
        if key in FILTER_KEYS:
            control.setToolTip(description)
        row = grid.rowCount()
        grid.addWidget(label_container, row, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(control, row, 2, Qt.AlignmentFlag.AlignTop)
        self.rows[section, key] = SettingRow(section, key, title, description, label_container, control, group)

    def save(self, model: BaseModel, section: str, key: str, value: SettingValue) -> bool:
        """Persist one setting; on validation failure show the error and restore the widget."""
        result = self._settings_store.set_value(model, section, key, value)
        if not result.success:
            self._reset_control(section, key, result.previous_value)
            QMessageBox.critical(
                self,
                "Error validating value",
                f"There was an error setting {key} to {value}. Your value has been reset to its previous version."
                f"\n\n{result.validation_error}",
            )
            return False
        if str(result.previous_value) == str(value):
            return True
        if key == "max_stash_tabs" and isinstance(model, GeneralModel):
            self._reset_control(section, "check_chest_tabs", model.check_chest_tabs)
        elif key == "vision_mode_type":
            prompt_restart(self)
        elif key in THEME_KEYS and self.theme_changed_callback:
            self.theme_changed_callback()
        return True

    def _reset_control(self, section: str, key: str, value: SettingValue) -> None:
        if row := self.rows.get((section, key)):
            reset_control(row.control, value)

    def _filter_settings(self, text: str) -> None:
        query = text.lower().strip()
        if not query:
            # Tabbed view: move group boxes back to their pages
            self.nav_list.show()
            self.stacked_widget.setCurrentIndex(self.nav_list.currentRow())
            for name, gb in self._group_boxes.items():
                gb.setVisible(True)
                self._pages[name].addWidget(gb)
            for row in self.rows.values():
                row.set_visible(True)
            return
        # Condensed view: move all group boxes into the search page
        if self.stacked_widget.currentWidget() != self.search_results_page:
            self.nav_list.hide()
            self.stacked_widget.addWidget(self.search_results_page)
            self.stacked_widget.setCurrentWidget(self.search_results_page)
            for gb in self._group_boxes.values():
                self.search_results_layout.addWidget(gb)
        for row in self.rows.values():
            row.set_visible(row.matches(query))
        for gb in self._group_boxes.values():
            # isHidden() is the row's own state; isVisible() would also reflect a hidden group box
            gb.setVisible(any(not row.label.isHidden() for row in self.rows.values() if row.group is gb))

    def show_tab(self) -> None:
        for model, section in self._settings_store.models_with_sections():
            self._reset_section(model, section)

    def reset_button_click(self) -> None:
        """Offer a reset of the current category or of all settings."""
        current_item = self.nav_list.currentItem()
        if not current_item or self.search_input.text():
            self._perform_global_reset()
            return
        tab_name = current_item.text()
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Reset Settings")
        msg.setText(f"Would you like to reset only the '{tab_name}' settings or all settings to defaults?")
        btn_tab = msg.addButton(f"Reset {tab_name}", QMessageBox.ButtonRole.ActionRole)
        btn_all = msg.addButton("Reset All Tabs", QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_all:
            self._perform_global_reset(confirm=True)
        elif clicked == btn_tab:
            self._reset_current_category(tab_name)

    def _perform_global_reset(self, confirm: bool = False) -> None:
        if confirm:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("This will reset ALL custom values in your params.ini. Are you sure?")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            if msg.exec() != QMessageBox.StandardButton.Ok:
                return
        self._settings_store.reset_all()
        self.show_tab()

    def _reset_current_category(self, category_name: str) -> None:
        group = self._group_boxes.get(category_name)
        settings = [
            (self._settings_store.model_for_section(row.section), row.section, row.key)
            for row in self.rows.values()
            if row.group is group
        ]
        changes = self._settings_store.reset_category(settings)
        for section in {section for section, _, _ in changes}:
            self._reset_section(self._settings_store.model_for_section(section), section)

    def _reset_section(self, model: BaseModel, section: str) -> None:
        for key, value in model:
            self._reset_control(section, key, value)
