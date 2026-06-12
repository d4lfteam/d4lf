from __future__ import annotations

import enum
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticUndefined
from PyQt6.QtCore import QCoreApplication, QSignalBlocker, Qt, QTimer
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
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
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
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
from src.gui.models.checkmark_checkbox import CheckmarkCheckBox

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
        group_box = QGroupBox(section_readable_header.replace("&", "&&"))
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
                if _validate_and_save_changes(model, section_config_header, config_key, val):
                    # Refresh the stash tabs widget to show the correct number of checkboxes
                    tabs_widget = self.model_to_parameter_value_map.get(f"{section_config_header}.check_chest_tabs")
                    if isinstance(tabs_widget, QChestTabWidget):
                        tabs_widget.reset_values(model.check_chest_tabs)

            parameter_value_widget = SegmentedControl(["6", "7"], str(config_value), on_tabs_changed)
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
                with QSignalBlocker(parameter_value_widget):
                    parameter_value_widget.addItems(options)
                    parameter_value_widget.setCurrentText(config_value)
                parameter_value_widget.currentTextChanged.connect(on_changed)

        elif isinstance(config_value, bool):
            parameter_value_widget = CheckmarkCheckBox()
            parameter_value_widget.setObjectName("switch")
            parameter_value_widget.setChecked(config_value)

            def on_bool_changed():
                _validate_and_save_changes(
                    model,
                    section_config_header,
                    config_key,
                    str(parameter_value_widget.isChecked()),
                    post_save_callback=(
                        self.theme_changed_callback
                        if config_key == "colorblind_mode" and not self._initializing
                        else None
                    ),
                )

            parameter_value_widget.stateChanged.connect(on_bool_changed)
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
        for _, _, _, control, gb in self._all_rows:
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
                QChestTabWidget | QHotkeyWidget | SegmentedControl | MultiSegmentedControl | IgnoreScrollWheelComboBox,
            ):
                parameter_value_widget.reset_values(config_value)  # type: ignore[attr-defined]
            elif isinstance(parameter_value_widget, QCheckBox):
                parameter_value_widget.setChecked(config_value)
            elif isinstance(parameter_value_widget, QSpinBox):
                parameter_value_widget.setValue(config_value)
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
        for label, val in items_map.items():
            btn = QPushButton(label)
            btn.setObjectName("segment-btn")
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            btn.setChecked(val in current_values)
            btn.clicked.connect(self._on_btn_clicked)
            layout.addWidget(btn)
            self.buttons[label] = btn

    def _on_btn_clicked(self):
        selected = [self.items_map[label] for label, btn in self.buttons.items() if btn.isChecked()]
        val_str = ",".join([v.name for v in selected])
        self.callback(val_str)

    def reset_values(self, values: list):
        for label, val in self.items_map.items():
            if label in self.buttons:
                self.buttons[label].setChecked(val in values)

    def setEnabled(self, enabled):  # noqa: N802
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

    def setEnabled(self, enabled):  # noqa: N802
        super().setEnabled(enabled)
        for btn in self.buttons.values():
            btn.setEnabled(enabled)


class IgnoreScrollWheelComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):  # noqa: N802
        if self.hasFocus():
            return QComboBox.wheelEvent(self, event)

        return event.ignore()

    def reset_values(self, value):
        with QSignalBlocker(self):
            self.setCurrentText(str(value))


class QChestTabWidget(QWidget):
    def __init__(self, model, section_header, config_key, chest_tab_config: list[int], max_chest_tabs):
        super().__init__()
        self.model = model
        self.section_header = section_header
        self.config_key = config_key
        self.all_checkboxes: list[CheckmarkCheckBox] = []
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.reset_values(chest_tab_config)

    def reset_values(self, chest_tab_config: list[int]):
        # Clear existing checkboxes
        while self.all_checkboxes:
            cb = self.all_checkboxes.pop()
            self.layout.removeWidget(cb)
            cb.deleteLater()

        max_tabs = self.model.max_stash_tabs
        for x in range(max_tabs):
            stash_checkbox = CheckmarkCheckBox(self)
            stash_checkbox.setText(str(x + 1))
            self.all_checkboxes.append(stash_checkbox)
            if x in chest_tab_config:
                stash_checkbox.setChecked(True)
            stash_checkbox.stateChanged.connect(
                lambda: self._save_changes_on_box_change(self.model, self.section_header, self.config_key)
            )
            self.layout.addWidget(stash_checkbox)

    def _save_changes_on_box_change(self, model, section_header, config_key):
        active_tabs = [check_box.text() for check_box in self.all_checkboxes if check_box.isChecked()]
        _validate_and_save_changes(model, section_header, config_key, ",".join(active_tabs), self.reset_values)


class QHotkeyWidget(QWidget):
    def __init__(self, model, section_header, config_key, current_value):
        super().__init__()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.open_picker_button = QPushButton()
        self.reset_values(current_value)
        self.open_picker_button.clicked.connect(
            lambda: self._launch_hotkey_dialog(model, section_header, config_key, self.open_picker_button.text())
        )
        self.open_picker_button.setProperty("hotkeyButton", True)  # noqa: FBT003
        layout.addWidget(self.open_picker_button)

        self.setLayout(layout)

    def reset_values(self, current_value):
        self.open_picker_button.setText(str(current_value))

    def _launch_hotkey_dialog(self, model, section_header, config_key, current_value):
        hotkey_dialog = HotkeyListenerDialog(self, current_value)
        if hotkey_dialog.exec():
            new_hotkey = hotkey_dialog.get_hotkey()
            if new_hotkey and _validate_and_save_changes(model, section_header, config_key, new_hotkey):
                self.open_picker_button.setText(new_hotkey)


class HotkeyListenerDialog(QDialog):  # type: ignore[misc]
    def __init__(self, parent=None, hotkey=""):
        super().__init__(parent)
        self.setWindowTitle("Set Hotkey")
        self.setModal(True)
        self.setFixedSize(320, 180)
        main_layout = QVBoxLayout(self)

        self.label = QLabel("Press the key or combination of keys you\nwant to use as a hotkey, then click save.", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.label)

        self.hotkey_label = QLabel(hotkey, self)
        self.hotkey_label.setObjectName("key-badge")
        self.hotkey_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.hotkey_label)

        self.button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save", self)
        self.save_button.setEnabled(False)
        self.save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.save_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancel_button.clicked.connect(self.reject)

        self.button_layout.addStretch()
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(self.button_layout)

        self.hotkey = hotkey

    def keyPressEvent(self, event):  # noqa: N802
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.reject()
            return

        modifiers = []
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier or key == Qt.Key.Key_Control:
            modifiers.append("ctrl")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier or key == Qt.Key.Key_Shift:
            modifiers.append("shift")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier or key == Qt.Key.Key_Alt:
            modifiers.append("alt")

        non_mod_key = ""
        if key not in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F35:
                non_mod_key = f"f{key - Qt.Key.Key_F1 + 1}"
            else:
                key_text = QKeySequence(key).toString().lower()
                if key_text:
                    non_mod_key = key_text

        parts = modifiers + ([non_mod_key] if non_mod_key else [])
        self.hotkey = "+".join(list(dict.fromkeys(parts)))
        self.hotkey_label.setText(self.hotkey)
        self.save_button.setEnabled(True)

    def get_hotkey(self):
        return self.hotkey
