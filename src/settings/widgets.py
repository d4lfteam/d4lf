import sys
from typing import TYPE_CHECKING, override

from PyQt6.QtCore import QSignalBlocker, Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.desktop.widgets import CheckmarkCheckBox
from src.settings.binding import validate_hotkey

if TYPE_CHECKING:
    from collections.abc import Callable

    from PyQt6.QtGui import QKeyEvent, QWheelEvent

    from src.settings import MoveItemsType
CONFIG_TABNAME = "config"


class MultiSegmentedControl(QWidget):
    def __init__(
        self, items_map: dict[str, MoveItemsType], current_values: list[MoveItemsType], callback: Callable[[str], None]
    ):
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

    def reset_values(self, values: list[MoveItemsType]) -> None:
        for label, val in self.items_map.items():
            if label in self.buttons:
                self.buttons[label].setChecked(val in values)

    @override
    def setEnabled(self, a0: bool) -> None:
        super().setEnabled(a0)
        for btn in self.buttons.values():
            btn.setEnabled(a0)


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

    @override
    def setEnabled(self, a0: bool) -> None:
        super().setEnabled(a0)
        for btn in self.buttons.values():
            btn.setEnabled(a0)


class IgnoreScrollWheelComboBox(QComboBox):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    @override
    def wheelEvent(self, e: QWheelEvent | None) -> None:
        if self.hasFocus():
            super().wheelEvent(e)
            return
        if e is not None:
            e.ignore()

    def reset_values(self, value):
        with QSignalBlocker(self):
            self.setCurrentText(str(value))


class QChestTabWidget(QWidget):
    def __init__(self, model, section_header, config_key, chest_tab_config: list[int], save_setting_value):
        super().__init__()
        self.model = model
        self.section_header = section_header
        self.config_key = config_key
        self._save_setting_value = save_setting_value
        self.all_checkboxes: list[CheckmarkCheckBox] = []
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.reset_values(chest_tab_config)

    def reset_values(self, chest_tab_config: list[int]):
        # Clear existing checkboxes
        while self.all_checkboxes:
            cb = self.all_checkboxes.pop()
            self._layout.removeWidget(cb)
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
            self._layout.addWidget(stash_checkbox)

    def _save_changes_on_box_change(self, model, section_header, config_key):
        active_tabs = [check_box.text() for check_box in self.all_checkboxes if check_box.isChecked()]

        def reset_chest_tabs(value: object) -> None:
            if not isinstance(value, list):
                return
            tabs: list[int] = []
            for tab in value:
                if not isinstance(tab, int):
                    return
                tabs.append(tab)
            self.reset_values(tabs)

        self._save_setting_value(model, section_header, config_key, ",".join(active_tabs), reset_chest_tabs)


class QHotkeyWidget(QWidget):
    def __init__(self, model, section_header, config_key, current_value, save_setting_value):
        super().__init__()
        self._save_setting_value = save_setting_value
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.open_picker_button = QPushButton()
        self.reset_values(current_value)
        self.open_picker_button.clicked.connect(
            lambda: self._launch_hotkey_dialog(model, section_header, config_key, self.open_picker_button.text())
        )
        self.open_picker_button.setProperty("hotkeyButton", True)  # ruff:ignore[boolean-positional-value-in-call]
        layout.addWidget(self.open_picker_button)
        self.setLayout(layout)

    def reset_values(self, current_value):
        self.open_picker_button.setText(str(current_value))

    def _launch_hotkey_dialog(self, model, section_header, config_key, current_value):
        hotkey_dialog = HotkeyListenerDialog(self, current_value)
        if hotkey_dialog.exec():
            new_hotkey = hotkey_dialog.get_hotkey()
            if new_hotkey and self._save_setting_value(model, section_header, config_key, new_hotkey):
                self.open_picker_button.setText(new_hotkey)


class HotkeyListenerDialog(QDialog):
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

    @override
    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if a0 is None:
            return
        key = a0.key()
        if key == Qt.Key.Key_Escape:
            self.reject()
            return
        modifiers = []
        # On macOS, Qt reports Command as ControlModifier and Control as MetaModifier.
        if a0.modifiers() & Qt.KeyboardModifier.ControlModifier or key == Qt.Key.Key_Control:
            modifiers.append("cmd" if sys.platform == "darwin" else "ctrl")
        if a0.modifiers() & Qt.KeyboardModifier.ShiftModifier or key == Qt.Key.Key_Shift:
            modifiers.append("shift")
        if a0.modifiers() & Qt.KeyboardModifier.AltModifier or key == Qt.Key.Key_Alt:
            modifiers.append("alt")
        if a0.modifiers() & Qt.KeyboardModifier.MetaModifier or key == Qt.Key.Key_Meta:
            modifiers.append("ctrl" if sys.platform == "darwin" else "cmd")
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
        try:
            self.hotkey = validate_hotkey(self.hotkey)
            self.save_button.setEnabled(True)
        except ValueError:
            self.save_button.setEnabled(False)
        self.hotkey_label.setText(self.hotkey)

    def get_hotkey(self):
        return self.hotkey
