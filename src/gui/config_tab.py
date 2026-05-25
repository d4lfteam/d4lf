import enum
import os
import subprocess
import sys
import typing
from pathlib import Path

from pydantic import BaseModel, ValidationError
from PyQt6.QtCore import QCoreApplication, Qt, QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config.loader import IniConfigLoader
from src.config.settings_models import HIDE_FROM_GUI_KEY, IS_HOTKEY_KEY, MoveItemsType
from src.gui.open_user_config_button import OpenUserConfigButton

CONFIG_TABNAME = "config"


def _validate_and_save_changes(
    model,
    header,
    key,
    value,
    method_to_reset_value: typing.Callable | None = None,
    post_save_callback: typing.Callable[[], None] | None = None,
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


LABEL_MAP = {
    "profiles": "Active Filtering Profiles",
    "auto_use_temper_manuals": "Auto-use Temper Manuals",
    "check_chest_tabs": "Stash Tabs to Filter",
    "do_not_junk_ancestral_legendaries": "Protective Ancestral Filter",
    "handle_uniques": "Unfiltered Unique Behavior",
    "keep_aspects": "Aspect Preservation Logic",
    "mark_as_favorite": "Mark Matched Items as Favorite",
    "colorblind_mode": "Colorblind Accessible Palette",
    "run_vision_mode_on_startup": "Auto-Start Vision Mode",
    "minimum_overlay_font_size": "Overlay Text Size",
    "log_lvl": "Logging Detail Level",
}

SUBGROUPS = {
    "Loot Behavior": [
        "profiles",
        "handle_uniques",
        "keep_aspects",
        "mark_as_favorite",
        "do_not_junk_ancestral_legendaries",
        "handle_cosmetics",
    ],
    "Automation": ["auto_use_temper_manuals", "run_vision_mode_on_startup", "ignore_escalation_sigils"],
    "UI & Theme": ["theme", "colorblind_mode", "minimum_overlay_font_size", "vision_mode_type"],
    "Stash & Transfer": ["check_chest_tabs", "max_stash_tabs", "move_to_inv_item_type", "move_to_stash_item_type"],
    "System & Paths": ["browser", "language"],
}


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
        action_bar.setStyleSheet("background-color: #121212; border-top: 1px solid #3c3c3c;")
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
        all_props = {}
        all_props.update({f"general.{k}": (loader.general, k, v) for k, v in loader.general})
        all_props.update({f"char.{k}": (loader.char, k, v) for k, v in loader.char})

        # Standard Subgroups
        for group_name, keys in SUBGROUPS.items():
            page = self._create_page(group_name)
            layout = page.findChild(QVBoxLayout)

            gb = QGroupBox(group_name)
            grid = QGridLayout(gb)
            grid.setColumnStretch(2, 1)

            for key in keys:
                lookup = f"general.{key}" if f"general.{key}" in all_props else f"char.{key}"
                if lookup not in all_props:
                    continue
                model, config_key, config_value = all_props[lookup]
                self._add_setting_row(
                    grid, grid.rowCount(), model, lookup.split(".", maxsplit=1)[0], config_key, config_value
                )

            layout.addWidget(gb)
            self._group_boxes[group_name] = gb

        # Hotkeys & Advanced Split
        self._build_advanced_and_hotkeys(loader.advanced_options)

    def _build_advanced_and_hotkeys(self, model):
        hotkey_page = self._create_page("Hotkeys")
        hk_gb = QGroupBox("Key Bindings")
        hk_grid = QGridLayout(hk_gb)
        hk_grid.setColumnStretch(2, 1)
        hotkey_page.findChild(QVBoxLayout).addWidget(hk_gb)
        self._group_boxes["Hotkeys"] = hk_gb

        adv_page = self._create_page("Advanced")
        adv_gb = QGroupBox("Technical Settings")
        adv_grid = QGridLayout(adv_gb)
        adv_grid.setColumnStretch(2, 1)
        adv_page.findChild(QVBoxLayout).addWidget(adv_gb)
        self._group_boxes["Advanced"] = adv_gb

        all_parameter_metadata = model.model_json_schema()["properties"]
        for config_key, config_value in model:
            is_hotkey = all_parameter_metadata[config_key].get(IS_HOTKEY_KEY) == "True"
            target_grid = hk_grid if is_hotkey else adv_grid
            self._add_setting_row(target_grid, target_grid.rowCount(), model, "advanced_options", config_key, config_value)

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

        human_label = LABEL_MAP.get(key, key.replace("_", " ").title())
        label_widget = QLabel(human_label)
        label_widget.setWordWrap(True)

        help_icon = QLabel("ⓘ")
        help_icon.setObjectName("help-icon")
        help_icon.setToolTip(f"<span>{meta.get('description', 'No description available.')}</span>")

        control = self._generate_parameter_value_widget(model, section, key, val, meta.get(IS_HOTKEY_KEY))
        self.model_to_parameter_value_map[f"{section}.{key}"] = control

        grid.addWidget(label_widget, row, 0)
        grid.addWidget(help_icon, row, 1)
        grid.addWidget(control, row, 2)
        self._all_rows.append((human_label, label_widget, help_icon, control, grid.parentWidget()))


    def _filter_settings(self, text):
        query = text.lower()
        if query:
            # Condensed View: Move all groupboxes into the search layout
            if self.stacked_widget.currentWidget() != self.search_results_page:
                self.nav_list.hide()
                self.stacked_widget.addWidget(self.search_results_page)
                self.stacked_widget.setCurrentWidget(self.search_results_page)
                for gb in self._group_boxes.values():
                    self.search_results_layout.addWidget(gb)

            for human_label, lbl, icon, ctrl, _ in self._all_rows:
                match = query in human_label.lower()
                lbl.setVisible(match)
                icon.setVisible(match)
                ctrl.setVisible(match)

            # Hide groupboxes that have no matching children
            for gb in self._group_boxes.values():
                has_visible = any(r[1].isVisible() for r in self._all_rows if r[4] == gb)
                gb.setVisible(has_visible)
        else:
            # Tabbed View: Move groupboxes back to their original pages
            self.nav_list.show()
            self.stacked_widget.setCurrentIndex(self.nav_list.currentRow())
            for name, gb in self._group_boxes.items():
                gb.setVisible(True)
                # Find the original page by name
                for i in range(self.stacked_widget.count()):
                    page_scroll = self.stacked_widget.widget(i)
                    if isinstance(page_scroll, QScrollArea) and self.nav_list.item(i).text() == name:
                        page_scroll.widget().layout().addWidget(gb)

            for r in self._all_rows:
                r[1].setVisible(True)
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
            parameter_value_widget = IgnoreScrollWheelComboBox()
            parameter_value_widget.addItems(["6", "7"])
            parameter_value_widget.setCurrentText(str(config_value))
            parameter_value_widget.currentTextChanged.connect(
                lambda: _validate_and_save_changes(
                    model, section_config_header, config_key, parameter_value_widget.currentText()
                )
            )
        elif config_key == "profiles":
            parameter_value_widget = QProfilesWidget(model, section_config_header, config_key, config_value)
        elif config_key in {"move_to_inv_item_type", "move_to_stash_item_type"}:
            parameter_value_widget = QMoveItemsWidget(model, section_config_header, config_key, config_value)
        elif is_hotkey:
            parameter_value_widget = QHotkeyWidget(model, section_config_header, config_key, config_value)
        elif isinstance(config_value, enum.StrEnum):
            parameter_value_widget = IgnoreScrollWheelComboBox()
            enum_type = type(config_value)

            # Block signals during initialization so we don't fire theme change with the old value
            parameter_value_widget.blockSignals(True)
            parameter_value_widget.addItems(list(enum_type))
            parameter_value_widget.setCurrentText(config_value)
            parameter_value_widget.blockSignals(False)

            def make_on_enum_changed(key):
                def on_enum_changed():
                    _validate_and_save_changes(
                        model,
                        section_config_header,
                        key,
                        parameter_value_widget.currentText(),
                        post_save_callback=(
                            self._prompt_restart_for_vision_mode_change
                            if key == "vision_mode_type" and not self._initializing
                            else None
                        ),
                    )

                    if key == "theme" and self.theme_changed_callback and not self._initializing:
                        self.theme_changed_callback()

                return on_enum_changed

            parameter_value_widget.currentTextChanged.connect(make_on_enum_changed(config_key))

        elif isinstance(config_value, bool):
            parameter_value_widget = QCheckBox()
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
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        message = "This will reset all custom values in your params.ini to their default value. Are you sure you want to continue?"
        msg.setText(message)
        msg.setWindowTitle("Reset to default values?")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)

        result = msg.exec()  # Store the result of msg.exec()

        if result == QMessageBox.StandardButton.Ok:
            IniConfigLoader().load(clear=True)
            self._reset_values_for_model(IniConfigLoader().general, "general")
            self._reset_values_for_model(IniConfigLoader().char, "char")
            self._reset_values_for_model(IniConfigLoader().advanced_options, "advanced_options")

    def _reset_values_for_model(self, model, section_config_header):
        for parameter in model:
            config_key, config_value = parameter
            parameter_value_widget = self.model_to_parameter_value_map.get(section_config_header + "." + config_key)
            # Should always exist but just being safe
            if parameter_value_widget is None:
                continue

            if isinstance(parameter_value_widget, QChestTabWidget | QProfilesWidget | QHotkeyWidget | QMoveItemsWidget):
                parameter_value_widget.reset_values(config_value)
            elif isinstance(parameter_value_widget, IgnoreScrollWheelComboBox):
                parameter_value_widget.blockSignals(True)
                parameter_value_widget.reset_values(config_value)
                parameter_value_widget.blockSignals(False)
            elif isinstance(parameter_value_widget, QCheckBox):
                parameter_value_widget.setChecked(config_value)
            else:
                parameter_value_widget.setText(str(config_value))

    def _setup_reset_button(self) -> QPushButton:
        reset_button = QPushButton("Reset to defaults")
        reset_button.clicked.connect(self.reset_button_click)
        return reset_button


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
        self.all_checkboxes: list[QCheckBox] = []
        stash_checkbox_layout = QHBoxLayout()
        stash_checkbox_layout.setContentsMargins(0, 0, 0, 0)
        for x in range(max_chest_tabs):
            stash_checkbox = QCheckBox(self)
            stash_checkbox.setText(str(x + 1))
            self.all_checkboxes.append(stash_checkbox)
            if x in chest_tab_config:
                stash_checkbox.setChecked(True)
            stash_checkbox.stateChanged.connect(
                lambda: self._save_changes_on_box_change(model, section_header, config_key)
            )
            stash_checkbox_layout.addWidget(stash_checkbox)

        self.setLayout(stash_checkbox_layout)

    def reset_values(self, chest_tab_config: list[int]):
        for check_box in self.all_checkboxes:
            check_box.setChecked(int(check_box.text()) - 1 in chest_tab_config)

    def _save_changes_on_box_change(self, model, section_header, config_key):
        active_tabs = [check_box.text() for check_box in self.all_checkboxes if check_box.isChecked()]
        _validate_and_save_changes(model, section_header, config_key, ",".join(active_tabs), self.reset_values)


class QMoveItemsWidget(QWidget):
    def __init__(self, model, section_header, config_key, move_selections: list[MoveItemsType]):
        super().__init__()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.current_move_selections_line_edit = QLineEdit()
        self.reset_values(move_selections)
        self.current_move_selections_line_edit.setReadOnly(True)
        layout.addWidget(self.current_move_selections_line_edit)

        open_picker_button = QPushButton()
        open_picker_button.setText("...")
        open_picker_button.setMinimumWidth(20)
        open_picker_button.clicked.connect(
            lambda: self._launch_picker(
                model, section_header, config_key, self.current_move_selections_line_edit.text().split(", ")
            )
        )
        layout.addWidget(open_picker_button)

        self.setLayout(layout)

    def reset_values(self, move_selections: list[MoveItemsType]):
        self.current_move_selections_line_edit.setText(", ".join([item_type.name for item_type in move_selections]))

    def _launch_picker(self, model, section_header, config_key, move_selections):
        move_item_type_picker = QMoveItemsPicker(self, move_selections)
        if move_item_type_picker.exec():
            move_types = move_item_type_picker.get_selected_move_types()
            move_types_string = ", ".join([item_type.name for item_type in move_types])
            _validate_and_save_changes(
                model, section_header, config_key, move_types_string, self.current_move_selections_line_edit.setText
            )
            self.reset_values(move_types)


class QMoveItemsPicker(QDialog):
    def __init__(self, parent, move_selections):
        super().__init__(parent)
        self.setWindowTitle("Select item types")
        layout = QVBoxLayout()

        label = QLabel("Select which item types you would like to move when hotkey is pressed.")
        self.move_favorite_box = QCheckBox("Favorite")
        self.move_junk_box = QCheckBox("Junk")
        self.move_unmarked_box = QCheckBox("Unmarked")

        self.move_favorite_box.setChecked(
            MoveItemsType.everything.name in move_selections or MoveItemsType.favorites.name in move_selections
        )
        self.move_junk_box.setChecked(
            MoveItemsType.everything.name in move_selections or MoveItemsType.junk.name in move_selections
        )
        self.move_unmarked_box.setChecked(
            MoveItemsType.everything.name in move_selections or MoveItemsType.unmarked.name in move_selections
        )

        layout.addWidget(label)
        layout.addWidget(self.move_favorite_box)
        layout.addWidget(self.move_junk_box)
        layout.addWidget(self.move_unmarked_box)

        ok_cancel_buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(ok_cancel_buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

    def get_selected_move_types(self) -> list[MoveItemsType]:
        result = []

        if self.move_favorite_box.isChecked():
            result.append(MoveItemsType.favorites)
        if self.move_junk_box.isChecked():
            result.append(MoveItemsType.junk)
        if self.move_unmarked_box.isChecked():
            result.append(MoveItemsType.unmarked)

        if not result or len(result) == 3:
            return [MoveItemsType.everything]

        return result


class QProfilesWidget(QWidget):
    def __init__(self, model, section_header, config_key, current_profiles):
        super().__init__()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.current_profile_line_edit = QLineEdit()
        self.reset_values(current_profiles)
        self.current_profile_line_edit.setReadOnly(True)
        layout.addWidget(self.current_profile_line_edit)

        open_picker_button = QPushButton()
        open_picker_button.setText("...")
        open_picker_button.setMinimumWidth(20)
        open_picker_button.clicked.connect(
            lambda: self._launch_picker(
                model, section_header, config_key, self.current_profile_line_edit.text().split(", ")
            )
        )
        layout.addWidget(open_picker_button)

        self.setLayout(layout)

    def reset_values(self, current_profiles):
        self.current_profile_line_edit.setText(", ".join(current_profiles))

    def _launch_picker(self, model, section_header, config_key, current_profiles):
        profile_picker = QProfilePicker(self, current_profiles)
        if profile_picker.exec():
            selected_profiles = ", ".join(profile_picker.get_selected_profiles())
            _validate_and_save_changes(
                model, section_header, config_key, selected_profiles, self.current_profile_line_edit.setText
            )
            self.current_profile_line_edit.setText(selected_profiles)


class QProfilePicker(QDialog):
    def __init__(self, parent, current_profiles):
        super().__init__(parent)
        self.setWindowTitle("Select profiles")

        overall_layout = QVBoxLayout()
        self.setGeometry(0, 0, 700, 500)

        profile_folder = IniConfigLoader().user_dir / "profiles"
        if not Path.exists(profile_folder):
            Path.mkdir(profile_folder)

        all_profile_files = profile_folder.iterdir()
        all_profiles = [
            os.path.splitext(profile_file.name)[0] for profile_file in all_profile_files if profile_file.is_file()
        ]
        all_profiles.sort(key=str.lower)

        self.disabled_profiles_list_widget = QListWidget()
        self.disabled_profiles_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.disabled_profiles_list_widget.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.disabled_profiles_list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)

        self.enabled_profiles_list_widget = QListWidget()
        self.enabled_profiles_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.enabled_profiles_list_widget.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.enabled_profiles_list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)

        for profile_name in all_profiles:
            if profile_name not in current_profiles:
                QListWidgetItem(profile_name, self.disabled_profiles_list_widget)

        for profile_name in current_profiles:
            if profile_name in all_profiles:
                QListWidgetItem(profile_name, self.enabled_profiles_list_widget)

        list_widget_layout = QGridLayout()
        list_widget_layout.addWidget(QLabel("Disabled Profiles"), 0, 0)
        list_widget_layout.addWidget(self.disabled_profiles_list_widget, 1, 0)

        # Create buttons for moving profiles between lists
        enable_button = QPushButton("Enable")
        enable_button.clicked.connect(
            lambda: self.move_items(self.disabled_profiles_list_widget, self.enabled_profiles_list_widget)
        )
        disable_button = QPushButton("Disable")
        disable_button.clicked.connect(
            lambda: self.move_items(self.enabled_profiles_list_widget, self.disabled_profiles_list_widget)
        )

        list_widget_layout.addWidget(enable_button, 2, 0)
        list_widget_layout.addWidget(disable_button, 2, 1)

        list_widget_layout.addWidget(QLabel("Enabled Profiles"), 0, 1)
        list_widget_layout.addWidget(self.enabled_profiles_list_widget, 1, 1)

        overall_layout.addLayout(list_widget_layout)

        message = QTextEdit(
            "Enable/Disable profiles by selecting and then using drag&drop or the buttons.\n"
            "Multi select is supported.\n"
            "You can change order by dragging a profile up and down in the right list."
        )
        message.setReadOnly(True)
        message.setFixedHeight(70)
        overall_layout.addWidget(message)

        ok_cancel_buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(ok_cancel_buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        overall_layout.addWidget(self.buttonBox)
        self.setLayout(overall_layout)

    def move_items(self, source_list, destination_list):
        for item in source_list.selectedItems():
            source_list.takeItem(source_list.row(item))
            destination_list.addItem(item)

    def get_selected_profiles(self):
        return [
            self.enabled_profiles_list_widget.item(x).text() for x in range(self.enabled_profiles_list_widget.count())
        ]


class QHotkeyWidget(QWidget):
    def __init__(self, model, section_header, config_key, current_value):
        super().__init__()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.open_picker_button = QPushButton()
        self.reset_values(current_value)
        self.open_picker_button.clicked.connect(lambda: self._launch_hotkey_dialog(model, section_header, config_key))
        self.open_picker_button.setProperty("hotkeyButton", True)
        layout.addWidget(self.open_picker_button)

        self.setLayout(layout)

    def reset_values(self, current_value):
        self.open_picker_button.setText(current_value)

    def _launch_hotkey_dialog(self, model, section_header, config_key):
        hotkey_dialog = HotkeyListenerDialog(self)
        if hotkey_dialog.exec():
            new_hotkey = hotkey_dialog.get_hotkey()
            if new_hotkey and _validate_and_save_changes(model, section_header, config_key, new_hotkey):
                self.open_picker_button.setText(new_hotkey)


class HotkeyListenerDialog(QDialog):
    def __init__(self, parent=None, hotkey=""):
        super().__init__(parent)
        self.setWindowTitle("Set Hotkey")
        self.hotkey = hotkey

        self.layout = QVBoxLayout(self)

        self.label = QLabel("Press the key or combination of keys you\nwant to use as a hotkey, then click save.", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.hotkey_label = QLabel(self.hotkey, self)
        self.hotkey_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.hotkey_label)

        self.button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save", self)
        self.cancel_button = QPushButton("Cancel", self)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.cancel_button)

        self.layout.addLayout(self.button_layout)

    def keyPressEvent(self, event):
        modifiers = []

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            modifiers.append("ctrl")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("shift")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            modifiers.append("alt")

        key = event.key()

        # Handle function keys
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F35:
            non_mod_key = f"f{key - Qt.Key.Key_F1 + 1}"

        # Handle regular keys
        else:
            text = event.text().lower()
            non_mod_key = text or ""

        # Build final hotkey string
        parts = modifiers + ([non_mod_key] if non_mod_key else [])
        hotkey_str = "+".join(parts)

        self.hotkey = hotkey_str
        self.hotkey_label.setText(hotkey_str)

    def get_hotkey(self):
        return self.hotkey
