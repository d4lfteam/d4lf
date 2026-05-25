from __future__ import annotations

import datetime
import enum
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from collections.abc import Callable

from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticUndefined
from PyQt6.QtCore import QCoreApplication, QMimeData, Qt, QTimer
from PyQt6.QtGui import QColor, QDrag, QKeySequence, QPainter, QPen
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QStyleOptionButton,
    QVBoxLayout,
    QWidget,
)

from src.config.loader import IniConfigLoader
from src.config.settings_models import (
    CATEGORY_KEY,
    CATEGORY_ORDER,
    HIDE_FROM_GUI_KEY,
    IS_HOTKEY_KEY,
    MoveItemsType,
    SettingsCategory,
)
from src.gui.open_user_config_button import OpenUserConfigButton

CONFIG_TABNAME = "config"


def _validate_and_save_changes(
    model,
    header,
    key,
    value,
    method_to_reset_value: Callable | None = None,
    post_save_callback: Callable[[], None] | None = None,
):
    current_value = getattr(model, key)
    try:
        validated_values = model.model_dump(mode="python")
        validated_values[key] = value
        type(model)(**validated_values)
        IniConfigLoader().save_value(header, key, value)
    except ValidationError as e:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)

        message = f"There was an error setting {key} to {value}. See error below.\n\n"

        # Only reset the widget if the field is NOT an enum
        if method_to_reset_value and key != "theme":
            message = message + "Your value has been reset to its previous version.\n\n"
            method_to_reset_value(str(current_value))

        message = message + str(e)
        msg.setText(message)
        msg.setWindowTitle("Error validating value")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        return False

    if post_save_callback and str(current_value) != str(value):
        post_save_callback()
    return True


class CheckmarkCheckBox(QCheckBox):
    """A custom QCheckBox that renders a checkmark inside its indicator.

    The checkmark is rendered when the box is checked, using the theme's accent color.
    """

    def paintEvent(self, event):
        super().paintEvent(event)  # Draw the default checkbox background/border

        if not self.isChecked():
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            option = QStyleOptionButton()
            self.initStyleOption(option)
            indicator_rect = self.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, self)

            # Draw a simple checkmark inside the indicator
            pen = QPen(QColor("#23fc5d"))  # Green color from theme
            pen.setWidth(2)  # Adjust thickness as needed
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            x0, y0, w, h = indicator_rect.x(), indicator_rect.y(), indicator_rect.width(), indicator_rect.height()

            # Checkmark coordinates (relative to indicator_rect) - Cast to int for PyQt6 compatibility
            painter.drawLine(int(x0 + w * 0.2), int(y0 + h * 0.5), int(x0 + w * 0.45), int(y0 + h * 0.75))
            painter.drawLine(int(x0 + w * 0.45), int(y0 + h * 0.75), int(x0 + w * 0.8), int(y0 + h * 0.25))
        finally:
            painter.end()


class ConfigTab(QWidget):
    def __init__(self, theme_changed_callback=None):
        self._initializing = True
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.theme_changed_callback = theme_changed_callback
        self.model_to_parameter_value_map = {}
        self._all_rows = []
        self._group_boxes = {}  # Store group boxes to move them during search

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)

        # Search Bar
        search_container = QWidget()
        search_hbox = QHBoxLayout(search_container)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search settings...")
        self.search_input.textChanged.connect(self._filter_settings)
        search_hbox.addWidget(self.search_input)
        layout.addWidget(search_container)

        # Main Content: Navigation List (Left) and Stacked Widget (Right)
        main_content = QWidget()
        content_hbox = QHBoxLayout(main_content)
        content_hbox.setContentsMargins(0, 0, 0, 0)
        content_hbox.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(160)
        self.nav_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                border-right: 1px solid #3c3c3c;
                outline: none;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #252525;
            }
            QListWidget::item:selected {
                background-color: #3c3c3c;
                color: #23fc5d;
                font-weight: bold;
            }
        """)

        self.stacked_widget = QStackedWidget()
        self.nav_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)

        content_hbox.addWidget(self.nav_list)
        content_hbox.addWidget(self.stacked_widget, stretch=1)
        layout.addWidget(main_content)

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
        action_hbox.addWidget(self._setup_reset_button())
        action_hbox.addStretch()
        action_hbox.addWidget(OpenUserConfigButton())
        layout.addWidget(action_bar)

        self.setLayout(layout)
        QTimer.singleShot(0, self._finish_init)

    def _finish_init(self):
        self._initializing = False

    def _build_sections(self):
        loader = IniConfigLoader()
        models = [(loader.general, "general"), (loader.char, "char"), (loader.advanced_options, "advanced_options")]

        # 1. Bucket settings by category using model metadata
        categories_map = {}
        for model, section in models:
            meta_all = model.model_json_schema()["properties"]
            for key, val in model:
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
                gb_title = str(cat_name)

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

    def _add_setting_row(self, grid, row, model, section, key, val):
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
        self._all_rows.append((human_label, meta.get("description", ""), label_container, control, grid.parentWidget()))

    def _filter_settings(self, text):
        query = text.lower().strip()
        if query:
            # Condensed View: Move all groupboxes into the search layout
            if self.stacked_widget.currentWidget() != self.search_results_page:
                self.nav_list.hide()
                self.stacked_widget.addWidget(self.search_results_page)
                self.stacked_widget.setCurrentWidget(self.search_results_page)
                for gb in self._group_boxes.values():
                    self.search_results_layout.addWidget(gb)

            for human_label, description_text, label_container, ctrl, _ in self._all_rows:
                # Check both setting title and description for matches
                match = query in (human_label or "").lower() or query in (description_text or "").lower()
                label_container.setVisible(match)
                ctrl.setVisible(match)

            # Hide groupboxes that have no matching children
            for gb in self._group_boxes.values():
                # We check isHidden() instead of isVisible() because isVisible() returns effective
                # visibility (including parents). If the groupbox was hidden previously, isVisible()
                # will always be False for children regardless of their individual visibility state.
                has_visible = any(not r[2].isHidden() for r in self._all_rows if r[4] == gb)
                gb.setVisible(has_visible)
        else:
            # Tabbed View: Move groupboxes back to their original pages
            self.nav_list.show()
            self.stacked_widget.setCurrentIndex(self.nav_list.currentRow())
            for name, gb in self._group_boxes.items():
                gb.setVisible(True)
                # Find the original page by name
                for i in range(self.nav_list.count()):
                    page_scroll = self.stacked_widget.widget(i)
                    if isinstance(page_scroll, QScrollArea) and self.nav_list.item(i).text() == name:
                        page_scroll.widget().layout().addWidget(gb)
                        break

            for r in self._all_rows:
                r[2].setVisible(True)
                r[3].setVisible(True)

    def _prompt_restart_for_vision_mode_change(self) -> None:
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Restart required")
        msg.setText("Vision mode changes require restarting d4lf. Restart now?")
        restart_button = msg.addButton("Restart now", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Later", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() is restart_button:
            self._restart_application()

    def _restart_application(self) -> None:
        command = [sys.executable, *sys.argv[1:]] if getattr(sys, "frozen", False) else [sys.executable, *sys.argv]

        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        try:
            subprocess.Popen(command, cwd=Path.cwd(), creationflags=creationflags)
        except OSError:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Restart failed")
            msg.setText("d4lf could not be restarted automatically. Please restart it manually.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            return

        if app := QCoreApplication.instance():
            app.quit()

    def _generate_params_section(self, model: BaseModel, section_readable_header: str, section_config_header: str):
        group_box = QGroupBox(section_readable_header)
        grid = QGridLayout(group_box)
        grid.setSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(2, 1)

        for i, (config_key, config_value) in enumerate(model):
            self._add_setting_row(grid, i, model, section_config_header, config_key, config_value)

        return group_box

    def _generate_parameter_value_widget(
        self, model: BaseModel, section_config_header, config_key, config_value, is_hotkey
    ):
        if config_key == "check_chest_tabs":
            parameter_value_widget = QChestTabWidget(
                model, section_config_header, config_key, config_value, IniConfigLoader().general.max_stash_tabs
            )
        elif config_key == "max_stash_tabs":

            def on_tabs_changed(val):
                _validate_and_save_changes(model, section_config_header, config_key, val)

            parameter_value_widget = SegmentedControl(["6", "7"], str(config_value), on_tabs_changed)
        elif config_key == "profiles":
            parameter_value_widget = QProfileListSelector(model, section_config_header, config_key, config_value)
        elif config_key in {"move_to_inv_item_type", "move_to_stash_item_type"}:
            items_map = {
                "Favorites": MoveItemsType.favorites,
                "Junk": MoveItemsType.junk,
                "Unmarked": MoveItemsType.unmarked,
            }

            def on_move_changed(val_str):
                _validate_and_save_changes(model, section_config_header, config_key, val_str)

            parameter_value_widget = MultiSegmentedControl(items_map, config_value, on_move_changed)
        elif is_hotkey:
            parameter_value_widget = QHotkeyWidget(model, section_config_header, config_key, str(config_value))
        elif isinstance(config_value, enum.StrEnum):
            enum_type = type(config_value)
            options = list(enum_type)

            def on_changed(new_text):
                _validate_and_save_changes(
                    model,
                    section_config_header,
                    config_key,
                    new_text,
                    post_save_callback=(
                        self._prompt_restart_for_vision_mode_change
                        if config_key == "vision_mode_type" and not self._initializing
                        else None
                    ),
                )
                if config_key == "theme" and self.theme_changed_callback and not self._initializing:
                    self.theme_changed_callback()

            if len(options) <= 3:
                parameter_value_widget = SegmentedControl(options, config_value, on_changed)
            else:
                parameter_value_widget = IgnoreScrollWheelComboBox()
                parameter_value_widget.blockSignals(True)
                parameter_value_widget.addItems(options)
                parameter_value_widget.setCurrentText(config_value)
                parameter_value_widget.blockSignals(False)
                parameter_value_widget.currentTextChanged.connect(on_changed)

        elif isinstance(config_value, bool):
            parameter_value_widget = CheckmarkCheckBox()
            parameter_value_widget.setObjectName("switch")
            parameter_value_widget.setChecked(config_value)
            parameter_value_widget.stateChanged.connect(
                lambda: _validate_and_save_changes(
                    model, section_config_header, config_key, str(parameter_value_widget.isChecked())
                )
            )
        elif isinstance(config_value, int):
            parameter_value_widget = QSpinBox()
            parameter_value_widget.setRange(0, 10000)
            parameter_value_widget.setValue(config_value)
            parameter_value_widget.valueChanged.connect(
                lambda: _validate_and_save_changes(
                    model, section_config_header, config_key, parameter_value_widget.value()
                )
            )
        else:
            parameter_value_widget = QLineEdit(str(config_value))
            parameter_value_widget.editingFinished.connect(
                lambda: _validate_and_save_changes(
                    model,
                    section_config_header,
                    config_key,
                    parameter_value_widget.text(),
                    method_to_reset_value=parameter_value_widget.setText,
                )
            )

        return parameter_value_widget

    def show_tab(self):
        self._reset_values_for_model(IniConfigLoader().general, "general")
        self._reset_values_for_model(IniConfigLoader().char, "char")
        self._reset_values_for_model(IniConfigLoader().advanced_options, "advanced_options")

    def reset_button_click(self):
        """Handle the reset button by offering tab-specific or global reset."""
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

    def _perform_global_reset(self, confirm: bool = False):
        if confirm:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("This will reset ALL custom values in your params.ini. Are you sure?")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            if msg.exec() != QMessageBox.StandardButton.Ok:
                return

        IniConfigLoader().load(clear=True)
        self.show_tab()

    def _reset_current_category(self, category_name: str):
        """Reset only the settings belonging to the active category."""
        target_gb = self._group_boxes.get(category_name)
        if not target_gb:
            return

        loader = IniConfigLoader()
        for _, _, control, gb in self._all_rows:
            if gb != target_gb:
                continue

            # Find the internal key for this control
            for key_path, widget in self.model_to_parameter_value_map.items():
                if widget == control:
                    section, key = key_path.split(".")
                    model = getattr(loader, section)

                    field = type(model).model_fields[key]
                    default_val = field.default if field.default is not PydanticUndefined else field.default_factory()

                    loader.save_value(section, key, default_val)
                    self._reset_values_for_model(model, section)
                    break

    def _reset_values_for_model(self, model, section_config_header):
        for parameter in model:
            config_key, config_value = parameter
            parameter_value_widget = self.model_to_parameter_value_map.get(section_config_header + "." + config_key)
            # Should always exist but just being safe
            if parameter_value_widget is None:
                continue

            if isinstance(
                parameter_value_widget,
                QChestTabWidget
                | QProfileListSelector
                | QHotkeyWidget
                | SegmentedControl
                | MultiSegmentedControl
                | IgnoreScrollWheelComboBox,
            ):
                parameter_value_widget.reset_values(config_value)  # type: ignore[attr-defined]
            elif isinstance(parameter_value_widget, QCheckBox):
                parameter_value_widget.setChecked(config_value)
            else:
                parameter_value_widget.setText(str(config_value))

    def _setup_reset_button(self) -> QPushButton:
        reset_button = QPushButton("Reset to defaults")
        reset_button.clicked.connect(self.reset_button_click)
        return reset_button


class MultiSegmentedControl(QWidget):
    def __init__(self, items_map: dict[str, Any], current_values: list, callback):
        super().__init__()
        self.callback = callback
        self.items_map = items_map
        self.setObjectName("segmented-container")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.buttons = {}
        is_everything = any(v == MoveItemsType.everything for v in current_values)
        for label, val in items_map.items():
            btn = QPushButton(label)
            btn.setObjectName("segment-btn")
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            btn.setChecked(is_everything or val in current_values)
            btn.clicked.connect(self._on_btn_clicked)
            layout.addWidget(btn)
            self.buttons[label] = btn

    def _on_btn_clicked(self):
        selected = [self.items_map[label] for label, btn in self.buttons.items() if btn.isChecked()]
        if not selected or len(selected) == len(self.items_map):
            val_str = "everything"
        else:
            val_str = ",".join([v.name for v in selected])
        self.callback(val_str)

    def reset_values(self, values: list):
        is_everything = any(v == MoveItemsType.everything for v in values)
        for label, val in self.items_map.items():
            if label in self.buttons:
                self.buttons[label].setChecked(is_everything or val in values)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        for btn in self.buttons.values():
            btn.setEnabled(enabled)


class SegmentedControl(QWidget):
    def __init__(self, items, current_value, callback):
        super().__init__()
        self.callback = callback
        self.setObjectName("segmented-container")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.group = QButtonGroup(self)
        self.buttons = {}

        for text in items:
            btn = QPushButton(str(text))
            btn.setObjectName("segment-btn")
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

            if text == current_value:
                btn.setChecked(True)

            self.group.addButton(btn)
            layout.addWidget(btn)
            self.buttons[str(text)] = btn

        self.group.buttonClicked.connect(self._on_btn_clicked)

    def _on_btn_clicked(self, btn):
        self.callback(btn.text())

    def reset_values(self, value):
        val_str = str(value)
        if val_str in self.buttons:
            self.buttons[val_str].setChecked(True)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        for btn in self.buttons.values():
            btn.setEnabled(enabled)


class IgnoreScrollWheelComboBox(QComboBox):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            return QComboBox.wheelEvent(self, event)

        return event.ignore()

    def reset_values(self, value):
        self.blockSignals(True)
        self.setCurrentText(str(value))
        self.blockSignals(False)


class QChestTabWidget(QWidget):
    def __init__(self, model, section_header, config_key, chest_tab_config: list[int], max_chest_tabs):
        super().__init__()
        self.all_checkboxes: list[CheckmarkCheckBox] = []
        stash_checkbox_layout = QHBoxLayout()
        stash_checkbox_layout.setContentsMargins(0, 0, 0, 0)
        for x in range(1, max_chest_tabs + 1):
            stash_checkbox = CheckmarkCheckBox(self)
            stash_checkbox.setText(str(x + 1))
            self.all_checkboxes.append(stash_checkbox)
            if x in chest_tab_config:  # type: ignore[operator]
                stash_checkbox.setChecked(True)
            stash_checkbox.stateChanged.connect(
                lambda: self._save_changes_on_box_change(model, section_header, config_key)
            )
            stash_checkbox_layout.addWidget(stash_checkbox)

        self.setLayout(stash_checkbox_layout)

    def reset_values(self, chest_tab_config: list[int]):
        for check_box in self.all_checkboxes:  # type: ignore[attr-defined]
            check_box.setChecked(int(check_box.text()) - 1 in chest_tab_config)

    def _save_changes_on_box_change(self, model, section_header, config_key):
        active_tabs = [check_box.text() for check_box in self.all_checkboxes if check_box.isChecked()]
        _validate_and_save_changes(model, section_header, config_key, ",".join(active_tabs), self.reset_values)


class QProfileListSelector(QWidget):
    def __init__(self, model, section, key, current_active: list[str]):
        super().__init__()
        self.model = model
        self.section = section
        self.key = key
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(5)

        self.setAcceptDrops(True)

        # Visual drop indicator for drag-and-drop
        self.drop_indicator = QFrame()
        self.drop_indicator.setFixedHeight(2)
        self.drop_indicator.setStyleSheet("background-color: #23fc5d;")
        self.drop_indicator.hide()

        # Search bar for profiles
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filter profiles...")
        self.search_input.textChanged.connect(self._filter_profiles)
        self._layout.addWidget(self.search_input)

        # Bulk selection buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.select_all_btn = QPushButton("Select All")
        self.deselect_all_btn = QPushButton("Deselect All")
        self.select_all_btn.clicked.connect(self._select_all)
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        btn_layout.addWidget(self.select_all_btn)
        btn_layout.addWidget(self.deselect_all_btn)
        btn_layout.addStretch()
        self._layout.addLayout(btn_layout)

        # Container for checkboxes to prevent refresh from deleting controls above
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(2)
        self._layout.addWidget(self.list_container)

        self._checkboxes: dict[str, CheckmarkCheckBox] = {}
        self._rows: dict[str, QWidget] = {}
        self.refresh(current_active)

    def refresh(self, current_active: list[str]):
        """Clear and repopulate the profile checkbox list."""
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if w := child.widget():
                w.deleteLater()
        self._checkboxes.clear()
        self._rows.clear()

        profiles_dir = IniConfigLoader().user_dir / "profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        all_files = list(profiles_dir.glob("*.yaml")) + list(profiles_dir.glob("*.yml"))
        file_map = {p.stem: p for p in all_files}

        if not all_files:
            lbl = QLabel("No profile files found in " + str(profiles_dir))
            lbl.setStyleSheet("color: #888; font-style: italic;")
            self.list_layout.addWidget(lbl)
            return

        # Order: Active profiles in their saved order first, then remaining alphabetical
        active_names = [n for n in current_active if n in file_map]
        remaining = sorted([n for n in file_map if n not in active_names], key=lambda x: x.lower())

        for name in active_names + remaining:
            p = file_map[name]
            row_widget = QWidget()
            row_widget.setProperty("profile_name", name)
            row_vbox = QVBoxLayout(row_widget)
            row_vbox.setContentsMargins(0, 0, 0, 5)
            row_vbox.setSpacing(0)

            header_container = QWidget()
            header_hbox = QHBoxLayout(header_container)
            header_hbox.setContentsMargins(0, 0, 0, 0)
            header_hbox.setSpacing(5)

            toggle_btn = self._create_row_btn("▶")
            drag_handle = self._create_row_btn("⠿")
            drag_handle.setCursor(Qt.CursorShape.SizeAllCursor)

            cb = CheckmarkCheckBox(name)
            cb.blockSignals(True)
            cb.setChecked(name in current_active)
            cb.blockSignals(False)
            cb.stateChanged.connect(self._on_toggle)

            header_hbox.addWidget(toggle_btn)
            header_hbox.addWidget(drag_handle)
            header_hbox.addWidget(cb)
            header_hbox.addStretch()

            summary_lbl = QLabel(self._get_profile_summary(p))
            summary_lbl.setObjectName("description-label")
            summary_lbl.setContentsMargins(30, 2, 10, 8)
            summary_lbl.setWordWrap(True)
            summary_lbl.setVisible(False)
            toggle_btn.clicked.connect(lambda _, lbl=summary_lbl, btn=toggle_btn: self._toggle_row(lbl, btn))

            # Connect drag handle to initiation logic
            drag_handle.mouseMoveEvent = lambda e, w=row_widget, h=drag_handle: self._start_drag(e, w, h)

            row_vbox.addWidget(header_container)
            row_vbox.addWidget(summary_lbl)
            self.list_layout.addWidget(row_widget)
            self._checkboxes[name] = cb
            self._rows[name] = row_widget

        # Re-apply any existing filter text
        if self.search_input.text():
            self._filter_profiles(self.search_input.text())

    def _select_all(self):
        for cb in self._checkboxes.values():
            cb.setChecked(True)
        self._on_toggle()

    def _deselect_all(self):
        for cb in self._checkboxes.values():
            cb.setChecked(False)
        self._on_toggle()

    def _on_toggle(self):
        active: list[str] = []
        for i in range(self.list_layout.count()):
            widget = self.list_layout.itemAt(i).widget()
            if widget:
                name = widget.property("profile_name")
                if name and self._checkboxes.get(name) and self._checkboxes[name].isChecked():
                    active.append(name)
        _validate_and_save_changes(self.model, self.section, self.key, ",".join(active), self.reset_values)

    def _start_drag(self, event, row_widget: QWidget, handle: QWidget):
        """Initiate the drag operation with a visual pickup animation."""
        if event.buttons() != Qt.MouseButton.LeftButton:
            return

        # Calculate hotspot relative to the row widget to prevent the ghost image from jumping.
        click_pos = handle.mapTo(row_widget, event.position().toPoint())

        drag = QDrag(row_widget)
        mime = QMimeData()
        # We use the internal object ID to safely track the widget being moved
        mime.setText(str(id(row_widget)))
        drag.setMimeData(mime)

        # Render a 'Ghost' of the entire row for the pickup animation
        pixmap = row_widget.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(click_pos)

        # Hide the original row temporarily during the drag for a cleaner look
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.3)
        row_widget.setGraphicsEffect(opacity_effect)

        # Initialize the landing line at the current spot
        idx = self.list_layout.indexOf(row_widget)
        self.list_layout.insertWidget(idx, self.drop_indicator)
        self.drop_indicator.show()

        drag.exec(Qt.DropAction.MoveAction)

        # Restore original appearance
        row_widget.setGraphicsEffect(None)
        self.drop_indicator.hide()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Handle the 'Sliding' reorder logic as the user drags."""
        source_id = event.mimeData().text()

        # Auto-scroll logic: Find the parent scroll area and adjust scrollbar if near edges
        parent_scroll = self.parentWidget()
        while parent_scroll and not isinstance(parent_scroll, QScrollArea):
            parent_scroll = parent_scroll.parentWidget()

        if parent_scroll:
            # Fix for AttributeError: Use position() and map relative to viewport
            global_pos = self.mapToGlobal(event.position().toPoint())
            viewport_pos = parent_scroll.viewport().mapFromGlobal(global_pos)
            margin = 40  # pixels from edge to trigger scroll
            if viewport_pos.y() < margin:
                sb = parent_scroll.verticalScrollBar()
                sb.setValue(sb.value() - 8)
            elif viewport_pos.y() > parent_scroll.viewport().height() - margin:
                sb = parent_scroll.verticalScrollBar()
                sb.setValue(sb.value() + 8)

        # Map the drag position to the list container's local coordinates
        pos = self.list_container.mapFrom(self, event.position().toPoint())

        dragged_row = None
        current_idx = -1

        # 1. Identify the row being dragged and its current position
        for i in range(self.list_layout.count()):
            w = self.list_layout.itemAt(i).widget()
            if w and str(id(w)) == source_id:
                dragged_row = w
                current_idx = i
                break

        if not dragged_row:
            return

        # 2. Check midpoint of other rows to determine if we should swap
        for i in range(self.list_layout.count()):
            target_row = self.list_layout.itemAt(i).widget()
            if not target_row or target_row in (dragged_row, self.drop_indicator):
                continue

            rect = target_row.geometry()
            mid_y = rect.center().y()

            # Only swap if the cursor has passed the vertical midpoint of the target row
            if (i > current_idx and pos.y() > mid_y) or (i < current_idx and pos.y() < mid_y):
                self.list_layout.insertWidget(i, self.drop_indicator)
                self.list_layout.insertWidget(i, dragged_row)
                break

        event.acceptProposedAction()

    def dropEvent(self, event):
        """Finalize the reorder and trigger a save."""
        self._on_toggle()
        event.acceptProposedAction()

    def _create_row_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(22, 22)
        btn.setFlat(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("font-weight: bold; border: none; background: transparent;")
        return btn

    def _toggle_row(self, label: QLabel, button: QPushButton):
        is_visible = not label.isVisible()
        label.setVisible(is_visible)
        button.setText("▼" if is_visible else "▶")

    def _filter_profiles(self, text: str):
        query = text.lower()
        for name, row in self._rows.items():
            row.setVisible(query in name.lower())

    def _get_profile_summary(self, path: Path) -> str:
        """Peeks into the YAML to build a summary tooltip."""
        try:
            stat = path.stat()
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.UTC).strftime("%Y-%m-%d %H:%M")
            size_kb = stat.st_size / 1024

            with path.open(encoding="utf-8") as f:
                # We use safe_load for a quick scan of the keys
                data = yaml.safe_load(f)

            if not data or not isinstance(data, dict):
                return f"Last Modified: {mtime}\nSize: {size_kb:.1f} KB\n(Empty or invalid profile)"

            summary = [f"Last Modified: {mtime}", f"Size: {size_kb:.1f} KB"]
            if affixes := data.get("Affixes"):
                types = set()
                for item in affixes:
                    if isinstance(item, dict):
                        # Each entry is { Name: { itemType: ... } }
                        spec = next(iter(item.values()))
                        if isinstance(spec, dict) and (it := spec.get("itemType")):
                            if isinstance(it, list):
                                types.update([str(t) for t in it])
                            else:
                                types.add(str(it))
                if types:
                    summary.append(f"📦 Items: {', '.join(sorted(types))}")
                summary.append(f"🔍 Affix Filters: {len(affixes)}")

            if aspects := data.get("AspectUpgrades"):
                summary.append(f"✨ Aspect Upgrades: {len(aspects)}")
            if uniques := data.get("GlobalUniques"):
                summary.append(f"💎 Global Uniques: {len(uniques)}")
            if data.get("Sigils"):
                summary.append("📜 Sigils: Included")
            if data.get("Tributes"):
                summary.append("🏆 Tributes: Included")
            if paragon := data.get("Paragon"):
                summary.append("🔱 Paragon Overlay: Data Found")
                if isinstance(paragon, dict) and (url := paragon.get("source_url")):
                    summary.append(f"🔗 Source: {url}")

            return "\n".join(summary)
        except Exception:
            return f"Path: {path}\n(Could not parse profile details)"

    def reset_values(self, active_list: list[str]):
        if isinstance(active_list, str):
            active_list = [p.strip() for p in active_list.split(",") if p.strip()]
        # Re-running refresh ensures the visual list order is updated to match the config
        self.refresh(active_list)


class QHotkeyWidget(QWidget):
    def __init__(self, model, section_header, config_key, current_value):
        super().__init__()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.open_picker_button = QPushButton()
        self.reset_values(current_value)
        self.open_picker_button.clicked.connect(
            lambda: self._launch_picker(model, section_header, config_key, self.open_picker_button.text())
        )
        layout.addWidget(self.open_picker_button)

        self.setLayout(layout)

    def reset_values(self, current_value):
        self.open_picker_button.setText(str(current_value))

    def _launch_picker(self, model, section_header, config_key, current_value):
        hotkey_dialog = HotkeyListenerDialog(self, current_value)
        if hotkey_dialog.exec():
            new_hotkey = hotkey_dialog.get_hotkey()
            _validate_and_save_changes(model, section_header, config_key, new_hotkey)
            self.open_picker_button.setText(new_hotkey)


class HotkeyListenerDialog(QDialog):  # type: ignore[misc]
    def __init__(self, parent=None, hotkey=""):
        super().__init__(parent)
        self.setWindowTitle("Hotkey Recorder")
        self.setModal(True)
        self.setFixedSize(300, 120)
        main_layout = QVBoxLayout(self)
        self.label = QLabel(f"Current: {hotkey}\n\nPress a new hotkey combination...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.label)
        self.hotkey = hotkey

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.reject()
            return
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        modifiers = event.modifiers()
        parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")

        key_text = QKeySequence(key).toString().lower()
        if key_text:
            parts.append(key_text)
            self.hotkey = "+".join(parts)
            self.accept()

    def get_hotkey(self):
        return self.hotkey
