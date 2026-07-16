from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QCheckBox, QGroupBox, QLineEdit, QListWidget, QMessageBox, QPushButton, QSpinBox, QWidget

from src.settings.widgets import (
    IgnoreScrollWheelComboBox,
    MultiSegmentedControl,
    QChestTabWidget,
    QHotkeyWidget,
    SegmentedControl,
)

if TYPE_CHECKING:
    from src.settings.store import SettingsStore

CONFIG_TABNAME = "config"


class ConfigResetMixin:
    _all_rows: list[tuple[str, str, QWidget, QWidget, QGroupBox]]
    _group_boxes: dict[str, QGroupBox]
    _settings_store: SettingsStore
    model_to_parameter_value_map: dict[str, QWidget]
    nav_list: QListWidget
    search_input: QLineEdit

    def show_tab(self):
        self._reset_values_for_model(self._settings_store.model_for_section("general"), "general")
        self._reset_values_for_model(self._settings_store.model_for_section("char"), "char")
        self._reset_values_for_model(self._settings_store.model_for_section("advanced_options"), "advanced_options")

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
        self._settings_store.reset_all()
        self.show_tab()

    def _reset_current_category(self, category_name: str):
        """Reset only the settings belonging to the active category."""
        target_gb = self._group_boxes.get(category_name)
        if not target_gb:
            return
        widget_to_key_path = {widget: key_path for key_path, widget in self.model_to_parameter_value_map.items()}
        category_settings = []
        for _, _, _, control, gb in self._all_rows:
            if gb != target_gb:
                continue
            key_path = widget_to_key_path.get(control)
            if key_path is None:
                continue
            section, key = key_path.split(".")
            category_settings.append((self._settings_store.model_for_section(section), section, key))
        if not category_settings:
            return
        changes = self._settings_store.reset_category(category_settings)
        for section in {section for section, _, _ in changes}:
            self._reset_values_for_model(self._settings_store.model_for_section(section), section)

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
                if isinstance(parameter_value_widget, QChestTabWidget):
                    if isinstance(config_value, list) and all(isinstance(value, int) for value in config_value):
                        parameter_value_widget.reset_values(config_value)
                else:
                    parameter_value_widget.reset_values(config_value)
            elif isinstance(parameter_value_widget, QCheckBox):
                parameter_value_widget.setChecked(config_value)
            elif isinstance(parameter_value_widget, QSpinBox):
                parameter_value_widget.setValue(config_value)
            elif isinstance(parameter_value_widget, QLineEdit):
                parameter_value_widget.setText(str(config_value))

    def _setup_reset_button(self) -> QPushButton:
        reset_button = QPushButton("Reset to defaults")
        reset_button.clicked.connect(self.reset_button_click)
        return reset_button
