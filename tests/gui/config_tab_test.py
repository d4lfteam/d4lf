import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from src.gui.config_tab import HotkeyListenerDialog


@pytest.fixture
def q_application():
    return QApplication.instance() or QApplication([])


def test_arrow_key_on_hotkey_dialog_button_sets_hotkey(q_application):
    assert q_application is not None
    dialog = HotkeyListenerDialog(hotkey="f8")
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.KeyboardModifier.ShiftModifier)

    try:
        assert dialog.eventFilter(dialog.save_button, event)
        assert dialog.get_hotkey() == "shift+left"
        assert dialog.hotkey_label.text() == "shift+left"
    finally:
        dialog.deleteLater()


def test_non_arrow_key_on_hotkey_dialog_button_keeps_default_button_handling(q_application):
    assert q_application is not None
    dialog = HotkeyListenerDialog(hotkey="f8")
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier)

    try:
        assert not dialog.eventFilter(dialog.save_button, event)
        assert dialog.get_hotkey() == "f8"
    finally:
        dialog.deleteLater()
