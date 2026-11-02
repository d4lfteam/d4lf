import enum
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import QCoreApplication, QSignalBlocker
from PyQt6.QtWidgets import QCheckBox, QLineEdit, QMessageBox, QSpinBox, QWidget

from src.desktop.widgets import CheckmarkCheckBox, IgnoreScrollWheelComboBox
from src.settings import GeneralModel, MoveItemsType
from src.settings.widgets import MultiSegmentedControl, QChestTabWidget, QHotkeyWidget, SaveSetting, SegmentedControl

if TYPE_CHECKING:
    from pydantic import BaseModel

    from src.settings.types import SettingValue

MAX_SEGMENTED_CONTROL_OPTIONS = 3
MOVE_ITEMS_MAP = {"Favorites": MoveItemsType.favorites, "Junk": MoveItemsType.junk, "Unmarked": MoveItemsType.unmarked}


def create_control(
    model: BaseModel, section: str, key: str, value: SettingValue, is_hotkey: bool, save: SaveSetting
) -> QWidget:
    """Build the editor widget for one setting; every edit is persisted through `save`."""

    def save_value(new_value: SettingValue) -> None:
        save(model, section, key, new_value)

    if key == "check_chest_tabs" and isinstance(model, GeneralModel):
        return QChestTabWidget(model, section, key, model.check_chest_tabs, save)
    if key == "max_stash_tabs":
        return SegmentedControl(["6", "7"], str(value), save_value)
    if key in {"move_to_inv_item_type", "move_to_stash_item_type"}:
        return MultiSegmentedControl(MOVE_ITEMS_MAP, cast("list[MoveItemsType]", value), save_value)
    if is_hotkey:
        return QHotkeyWidget(model, section, key, str(value), save)
    if isinstance(value, enum.StrEnum):
        options: list[SettingValue] = [str(option) for option in type(value)]
        if len(options) <= MAX_SEGMENTED_CONTROL_OPTIONS:
            return SegmentedControl(options, value, save_value)
        combo = IgnoreScrollWheelComboBox()
        with QSignalBlocker(combo):
            combo.addItems([str(option) for option in options])
            combo.setCurrentText(value)
        combo.currentTextChanged.connect(save_value)
        return combo
    if isinstance(value, bool):
        checkbox = CheckmarkCheckBox()
        checkbox.setObjectName("switch")
        checkbox.setChecked(value)
        checkbox.stateChanged.connect(lambda: save_value(str(checkbox.isChecked())))
        return checkbox
    if isinstance(value, int):
        spin_box = QSpinBox()
        spin_box.setRange(0, 10000)
        spin_box.setValue(value)
        spin_box.valueChanged.connect(save_value)
        return spin_box
    line_edit = QLineEdit(str(value))
    line_edit.editingFinished.connect(lambda: save_value(line_edit.text()))
    return line_edit


def reset_control(control: QWidget, value: SettingValue) -> None:
    """Show `value` in a widget built by `create_control`."""
    if isinstance(control, QChestTabWidget):
        if isinstance(value, list) and all(isinstance(tab, int) for tab in value):
            control.reset_values(cast("list[int]", value))
    elif isinstance(control, QHotkeyWidget | SegmentedControl):
        control.reset_values(value)
    elif isinstance(control, IgnoreScrollWheelComboBox):
        with QSignalBlocker(control):
            control.setCurrentText(str(value))
    elif isinstance(control, MultiSegmentedControl):
        control.reset_values(cast("list[MoveItemsType]", value))
    elif isinstance(control, QCheckBox):
        if isinstance(value, bool):
            control.setChecked(value)
    elif isinstance(control, QSpinBox):
        if isinstance(value, int) and not isinstance(value, bool):
            control.setValue(value)
    elif isinstance(control, QLineEdit):
        control.setText(str(value))


def prompt_restart(parent: QWidget) -> None:
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Question)
    msg.setWindowTitle("Restart required")
    msg.setText("Vision mode changes require restarting d4lf. Restart now?")
    restart_button = msg.addButton("Restart now", QMessageBox.ButtonRole.AcceptRole)
    msg.addButton("Later", QMessageBox.ButtonRole.RejectRole)
    msg.exec()
    if msg.clickedButton() is not restart_button:
        return
    command = [sys.executable, *sys.argv[1:]] if getattr(sys, "frozen", False) else [sys.executable, *sys.argv]
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if sys.platform == "win32" else 0
    try:
        subprocess.Popen(command, cwd=Path.cwd(), creationflags=creationflags)
    except OSError:
        QMessageBox.critical(
            parent, "Restart failed", "d4lf could not be restarted automatically. Please restart it manually."
        )
        return
    if app := QCoreApplication.instance():
        app.quit()
