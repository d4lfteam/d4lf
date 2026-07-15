import importlib
import sys
import types

import pytest


@pytest.fixture
def window_module(monkeypatch):
    win32gui = types.ModuleType("win32gui")
    win32gui.__dict__["ClientToScreen"] = lambda *_: (0, 0)
    win32gui.__dict__["EnumWindows"] = lambda *_: None
    win32gui.__dict__["GetClientRect"] = lambda *_: (0, 0, 0, 0)
    win32gui.__dict__["GetWindowText"] = lambda *_: "Diablo IV"

    win32process = types.ModuleType("win32process")
    win32process.__dict__["GetWindowThreadProcessId"] = lambda *_: (0, 0)

    pywintypes = types.ModuleType("pywintypes")
    pywintypes.__dict__["error"] = OSError

    cam = types.ModuleType("src.cam")
    cam.__dict__["Cam"] = object

    monkeypatch.setitem(sys.modules, "win32gui", win32gui)
    monkeypatch.setitem(sys.modules, "win32process", win32process)
    monkeypatch.setitem(sys.modules, "pywintypes", pywintypes)
    monkeypatch.setitem(sys.modules, "src.cam", cam)
    monkeypatch.delitem(sys.modules, "src.utils.window", raising=False)
    monkeypatch.delitem(sys.modules, "src.utils.window_backend_windows", raising=False)

    window = importlib.import_module("src.utils.window")
    backend = importlib.import_module("src.utils.window_backend_windows")
    monkeypatch.setattr(window, "_platform_backend", backend)
    yield window
    monkeypatch.delitem(sys.modules, "src.utils.window", raising=False)
    monkeypatch.delitem(sys.modules, "src.utils.window_backend_windows", raising=False)


def test_skips_window_with_invalid_pid_when_finding_process(window_module, mocker):
    backend = window_module._platform_backend
    mocker.patch.object(backend, "list_active_window_ids", return_value=[1, 2])
    mocker.patch.object(backend, "GetWindowThreadProcessId", side_effect=[(0, -12865840), (0, 42)])
    process = mocker.patch.object(backend.psutil, "Process")
    diablo_process = mocker.Mock()
    diablo_process.name.return_value = "Diablo IV.exe"
    process.side_effect = [ValueError("pid must be a positive integer"), diablo_process]

    hwnd = window_module.get_window_spec_id(window_module.WindowSpec("Diablo IV.exe"))

    assert hwnd == 2


def test_resets_window_position_when_diablo_window_closes(window_module, mocker):
    backend = window_module._platform_backend
    camera = mocker.Mock()
    mocker.patch.object(backend, "Cam", return_value=camera)
    mocker.patch.object(backend, "get_window_spec_id", return_value=None)
    mocker.patch.object(backend.time, "sleep")

    window_module.find_and_set_window_position(window_module.WindowSpec("Diablo IV.exe"))

    camera.reset_window_position.assert_called_once_with()


def test_resets_window_position_when_diablo_window_closes_during_geometry_lookup(window_module, mocker):
    backend = window_module._platform_backend
    camera = mocker.Mock()
    mocker.patch.object(backend, "Cam", return_value=camera)
    mocker.patch.object(backend, "get_window_spec_id", return_value=1)
    mocker.patch.object(backend, "GetClientRect", side_effect=OSError("invalid window handle"))
    mocker.patch.object(backend.time, "sleep")

    window_module.find_and_set_window_position(window_module.WindowSpec("Diablo IV.exe"))

    camera.reset_window_position.assert_called_once_with()


def test_backend_adapter_forwards_selected_backend(window_module, mocker):
    adapter = window_module._WindowBackendAdapter()
    mocker.patch.object(window_module._platform_backend, "is_self_foreground", return_value=True)

    assert adapter.is_self_foreground()
