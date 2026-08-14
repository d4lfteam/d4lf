import sys
import typing

import pytest

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

from src import automation
from src.automation.window import core as _window


def test_window_spec_matches_process_and_window_name(monkeypatch) -> None:
    monkeypatch.setattr(_window._backend, "get_window_name_from_id", lambda _: "Diablo IV")
    monkeypatch.setattr(_window._backend, "get_process_from_window_name", lambda _: "diablo iv.exe")
    assert _window.WindowSpec("Diablo IV.exe").match(1)
    assert _window._platform_backend is _window.window_backend_noop if sys.platform != "win32" else True


def test_non_windows_window_adapter_is_safe_for_the_public_interface() -> None:
    if sys.platform == "win32":
        pytest.skip("No-op adapter behavior is non-Windows only")
    window = automation.WindowSpec("Diablo IV.exe")

    assert automation.get_window_spec_id(window) is None
    assert not automation.is_window_foreground(window)
    assert not automation.is_self_foreground()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows backend selection")
def test_windows_window_adapter_selects_windows_backend() -> None:
    assert _window._platform_backend.__name__.endswith("backend_windows")


def test_hotkey_interface_delegates_to_configured_input_backend(monkeypatch, mocker: MockerFixture) -> None:
    send = mocker.Mock()
    monkeypatch.setattr("src.settings.hotkeys.send", send)

    automation.send_hotkey("ctrl+f11")

    send.assert_called_once_with("ctrl+f11")


def test_public_window_interface_uses_the_selected_backend(monkeypatch, mocker: MockerFixture) -> None:
    backend = mocker.Mock()
    backend.get_window_spec_id.return_value = 42
    monkeypatch.setattr(_window, "_backend", backend)
    window = automation.WindowSpec("Diablo IV.exe")

    assert automation.get_window_spec_id(window) == 42
    backend.get_window_spec_id.assert_called_once_with(window)
