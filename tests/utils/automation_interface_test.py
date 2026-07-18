from unittest.mock import Mock

from src import automation
from src.automation import _window


def test_non_windows_window_adapter_is_safe_for_the_public_interface() -> None:
    window = automation.WindowSpec("Diablo IV.exe")

    assert automation.get_window_spec_id(window) is None
    assert not automation.is_window_foreground(window)
    assert not automation.is_self_foreground()


def test_hotkey_interface_delegates_to_configured_input_backend(monkeypatch) -> None:
    send = Mock()
    monkeypatch.setattr("src.settings.send", send)

    automation.send_hotkey("ctrl+f11")

    send.assert_called_once_with("ctrl+f11")


def test_public_window_interface_uses_the_selected_backend(monkeypatch) -> None:
    backend = Mock()
    backend.get_window_spec_id.return_value = 42
    monkeypatch.setattr(_window, "_backend", backend)
    window = automation.WindowSpec("Diablo IV.exe")

    assert automation.get_window_spec_id(window) == 42
    backend.get_window_spec_id.assert_called_once_with(window)
