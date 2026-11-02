import sys
from typing import TYPE_CHECKING, override

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QButtonGroup, QDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from src.desktop.widgets import CheckmarkCheckBox
from src.settings.binding import validate_hotkey

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel
    from PyQt6.QtGui import QKeyEvent

    from src.settings import GeneralModel, MoveItemsType
    from src.settings.types import SettingValue

type SaveSetting = Callable[[BaseModel, str, str, SettingValue], bool]


class MultiSegmentedControl(QWidget):
    def __init__(
        self, items_map: dict[str, MoveItemsType], current_values: list[MoveItemsType], callback: Callable[[str], None]
    ) -> None:
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

    def _on_btn_clicked(self) -> None:
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
    def __init__(self, items: list[SettingValue], current_value: SettingValue, callback: Callable[[str], None]) -> None:
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

    def _on_btn_clicked(self, btn: QPushButton) -> None:
        self.callback(btn.text())

    def reset_values(self, value: SettingValue) -> None:
        val_str = str(value)
        if val_str in self.buttons:
            self.buttons[val_str].setChecked(True)

    @override
    def setEnabled(self, a0: bool) -> None:
        super().setEnabled(a0)
        for btn in self.buttons.values():
            btn.setEnabled(a0)


class QChestTabWidget(QWidget):
    def __init__(
        self, model: GeneralModel, section: str, key: str, chest_tab_config: list[int], save: SaveSetting
    ) -> None:
        super().__init__()
        self.model = model
        self.section = section
        self.key = key
        self._save = save
        self.all_checkboxes: list[CheckmarkCheckBox] = []
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.reset_values(chest_tab_config)

    def reset_values(self, chest_tab_config: list[int]) -> None:
        while self.all_checkboxes:
            cb = self.all_checkboxes.pop()
            self._layout.removeWidget(cb)
            cb.deleteLater()
        for x in range(self.model.max_stash_tabs):
            stash_checkbox = CheckmarkCheckBox(self)
            stash_checkbox.setText(str(x + 1))
            self.all_checkboxes.append(stash_checkbox)
            stash_checkbox.setChecked(x in chest_tab_config)
            stash_checkbox.stateChanged.connect(self._save_checked_tabs)
            self._layout.addWidget(stash_checkbox)

    def _save_checked_tabs(self) -> None:
        active_tabs = [check_box.text() for check_box in self.all_checkboxes if check_box.isChecked()]
        self._save(self.model, self.section, self.key, ",".join(active_tabs))


class QHotkeyWidget(QWidget):
    def __init__(
        self, model: BaseModel, section: str, key: str, current_value: SettingValue, save: SaveSetting
    ) -> None:
        super().__init__()
        self._save = save
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.open_picker_button = QPushButton()
        self.reset_values(current_value)
        self.open_picker_button.clicked.connect(
            lambda: self._launch_hotkey_dialog(model, section, key, self.open_picker_button.text())
        )
        self.open_picker_button.setProperty("hotkeyButton", True)  # ruff:ignore[FBT003]
        layout.addWidget(self.open_picker_button)
        self.setLayout(layout)

    def reset_values(self, current_value: SettingValue) -> None:
        self.open_picker_button.setText(str(current_value))

    def _launch_hotkey_dialog(self, model: BaseModel, section: str, key: str, current_value: str) -> None:
        hotkey_dialog = HotkeyListenerDialog(self, current_value)
        if hotkey_dialog.exec():
            new_hotkey = hotkey_dialog.get_hotkey()
            if new_hotkey and self._save(model, section, key, new_hotkey):
                self.open_picker_button.setText(new_hotkey)


class HotkeyListenerDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, hotkey: str = "") -> None:
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
        self.hotkey: str = hotkey

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

    def get_hotkey(self) -> str:
        return self.hotkey
