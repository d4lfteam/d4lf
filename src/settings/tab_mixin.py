import enum
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import QCoreApplication, QSignalBlocker
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.desktop.widgets import CheckmarkCheckBox
from src.settings import GeneralModel, MoveItemsType
from src.settings.widgets import (
    IgnoreScrollWheelComboBox,
    MultiSegmentedControl,
    QChestTabWidget,
    QHotkeyWidget,
    SegmentedControl,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel

    from src.settings.store import SettingsStore
    from src.settings.types import SettingValue
CONFIG_TABNAME = "config"


class ConfigTabMixin:
    _all_rows: list[tuple[str, str, QWidget, QWidget, QGroupBox]]
    _group_boxes: dict[str, QGroupBox]
    _initializing: bool
    _settings_store: SettingsStore
    model_to_parameter_value_map: dict[str, QWidget]
    nav_list: QListWidget
    search_results_layout: QVBoxLayout
    search_results_page: QScrollArea
    stacked_widget: QStackedWidget
    theme_changed_callback: Callable[[], None] | None

    if TYPE_CHECKING:

        def _add_setting_row(
            self, grid: QGridLayout, row: int, model: BaseModel, section: str, key: str, val: SettingValue
        ) -> None: ...

    def _filter_settings(self, text: str) -> None:
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
                    if not isinstance(page_scroll, QScrollArea):
                        continue
                    nav_item = self.nav_list.item(i)
                    page_widget = page_scroll.widget()
                    if nav_item is None or page_widget is None or nav_item.text() != name:
                        continue
                    page_layout = page_widget.layout()
                    if page_layout is not None:
                        page_layout.addWidget(gb)
                    break
            for r in self._all_rows:
                r[2].setVisible(True)
                r[3].setVisible(True)

    def _prompt_restart_for_vision_mode_change(self) -> None:
        msg = QMessageBox(cast("QWidget", self))
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
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        try:
            subprocess.Popen(command, cwd=Path.cwd(), creationflags=creationflags)
        except OSError:
            msg = QMessageBox(cast("QWidget", self))
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Restart failed")
            msg.setText("d4lf could not be restarted automatically. Please restart it manually.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            return
        if app := QCoreApplication.instance():
            app.quit()

    def _save_setting_value(
        self,
        model: BaseModel,
        section_header: str,
        key: str,
        value: SettingValue,
        method_to_reset_value: Callable[[SettingValue], None] | None = None,
        post_save_callback: Callable[[], None] | None = None,
    ) -> bool:
        result = self._settings_store.set_value(model, section_header, key, value)
        if not result.success:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            message = f"There was an error setting {key} to {value}. See error below.\n\n"
            # Only reset the widget if the field is NOT an enum
            if method_to_reset_value and key != "theme":
                message = message + "Your value has been reset to its previous version.\n\n"
                method_to_reset_value(result.previous_value)
            message = message + str(result.validation_error)
            msg.setText(message)
            msg.setWindowTitle("Error validating value")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            return False
        if post_save_callback and str(result.previous_value) != str(value):
            post_save_callback()
        return True

    def _generate_params_section(
        self, model: BaseModel, section_readable_header: str, section_config_header: str
    ) -> QGroupBox:
        group_box = QGroupBox(section_readable_header.replace("&", "&&"))
        grid = QGridLayout(group_box)
        grid.setSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(2, 1)
        for i, (config_key, config_value) in enumerate(model):
            self._add_setting_row(grid, i, model, section_config_header, config_key, config_value)
        return group_box

    def _generate_parameter_value_widget(
        self, model: BaseModel, section_config_header: str, config_key: str, config_value: SettingValue, is_hotkey: bool
    ) -> QWidget:
        if config_key == "check_chest_tabs":
            if not isinstance(model, GeneralModel):
                msg = "check_chest_tabs is only available in GeneralModel"
                raise TypeError(msg)
            parameter_value_widget = QChestTabWidget(
                model, section_config_header, config_key, cast("list[int]", config_value), self._save_setting_value
            )
        elif config_key == "max_stash_tabs":
            if not isinstance(model, GeneralModel):
                msg = "max_stash_tabs is only available in GeneralModel"
                raise TypeError(msg)
            settings_model = model

            def on_tabs_changed(val: str) -> None:
                if self._save_setting_value(settings_model, section_config_header, config_key, val):
                    # Refresh the stash tabs widget to show the correct number of checkboxes
                    tabs_widget = self.model_to_parameter_value_map.get(f"{section_config_header}.check_chest_tabs")
                    if isinstance(tabs_widget, QChestTabWidget):
                        tabs_widget.reset_values(settings_model.check_chest_tabs)

            parameter_value_widget = SegmentedControl(["6", "7"], str(config_value), on_tabs_changed)
        elif config_key in {"move_to_inv_item_type", "move_to_stash_item_type"}:
            items_map = {
                "Favorites": MoveItemsType.favorites,
                "Junk": MoveItemsType.junk,
                "Unmarked": MoveItemsType.unmarked,
            }

            def on_move_changed(val_str: str) -> None:
                self._save_setting_value(model, section_config_header, config_key, val_str)

            parameter_value_widget = MultiSegmentedControl(
                items_map, cast("list[MoveItemsType]", config_value), on_move_changed
            )
        elif is_hotkey:
            parameter_value_widget = QHotkeyWidget(
                model, section_config_header, config_key, str(config_value), self._save_setting_value
            )
        elif isinstance(config_value, enum.StrEnum):
            enum_type = type(config_value)
            options: list[SettingValue] = []
            options.extend(str(option) for option in enum_type)

            def on_changed(new_text: str) -> None:
                self._save_setting_value(
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
                    parameter_value_widget.addItems([str(option) for option in options])
                    parameter_value_widget.setCurrentText(config_value)
                parameter_value_widget.currentTextChanged.connect(on_changed)
        elif isinstance(config_value, bool):
            checkbox = CheckmarkCheckBox()
            checkbox.setObjectName("switch")
            checkbox.setChecked(config_value)
            if config_key in {"filter_equipment", "filter_sigils", "filter_tributes", "filter_seals", "filter_charms"}:
                description = type(model).model_json_schema()["properties"].get(config_key, {}).get("description", "")
                checkbox.setToolTip(description)

            def on_bool_changed() -> None:
                self._save_setting_value(
                    model,
                    section_config_header,
                    config_key,
                    str(checkbox.isChecked()),
                    post_save_callback=(
                        self.theme_changed_callback
                        if config_key == "colorblind_mode" and not self._initializing
                        else None
                    ),
                )

            checkbox.stateChanged.connect(on_bool_changed)
            parameter_value_widget = checkbox
        elif isinstance(config_value, int):
            spin_box = QSpinBox()
            spin_box.setRange(0, 10000)
            spin_box.setValue(config_value)
            spin_box.valueChanged.connect(
                lambda: self._save_setting_value(model, section_config_header, config_key, spin_box.value())
            )
            parameter_value_widget = spin_box
        else:
            parameter_value_widget = QLineEdit(str(config_value))
            parameter_value_widget.editingFinished.connect(
                lambda: self._save_setting_value(
                    model,
                    section_config_header,
                    config_key,
                    parameter_value_widget.text(),
                    method_to_reset_value=lambda value: parameter_value_widget.setText(str(value)),
                )
            )
        return parameter_value_widget
