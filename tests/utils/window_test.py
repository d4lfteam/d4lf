import importlib
import sys
import types

import pytest


@pytest.fixture
def window_module(monkeypatch):
    win32gui = types.ModuleType("win32gui")
    win32gui.ClientToScreen = lambda *_: (0, 0)
    win32gui.EnumWindows = lambda *_: None
    win32gui.GetClientRect = lambda *_: (0, 0, 0, 0)
    win32gui.GetWindowText = lambda *_: "Diablo IV"

    win32process = types.ModuleType("win32process")
    win32process.GetWindowThreadProcessId = lambda *_: (0, 0)

    pywintypes = types.ModuleType("pywintypes")
    pywintypes.error = OSError

    cam = types.ModuleType("src.cam")
    cam.Cam = object

    monkeypatch.setitem(sys.modules, "win32gui", win32gui)
    monkeypatch.setitem(sys.modules, "win32process", win32process)
    monkeypatch.setitem(sys.modules, "pywintypes", pywintypes)
    monkeypatch.setitem(sys.modules, "src.cam", cam)
    monkeypatch.delitem(sys.modules, "src.utils.window", raising=False)

    yield importlib.import_module("src.utils.window")
    monkeypatch.delitem(sys.modules, "src.utils.window", raising=False)


def test_skips_window_with_invalid_pid_when_finding_process(window_module, mocker):
    mocker.patch.object(window_module, "_list_active_window_ids", return_value=[1, 2])
    mocker.patch.object(window_module, "GetWindowThreadProcessId", side_effect=[(0, -12865840), (0, 42)])
    process = mocker.patch.object(window_module.psutil, "Process")
    diablo_process = mocker.Mock()
    diablo_process.name.return_value = "Diablo IV.exe"
    process.side_effect = [ValueError("pid must be a positive integer"), diablo_process]

    hwnd = window_module.get_window_spec_id(window_module.WindowSpec("Diablo IV.exe"))

    assert hwnd == 2


def test_resets_window_position_when_diablo_window_closes(window_module, mocker):
    camera = mocker.Mock()
    mocker.patch.object(window_module, "Cam", return_value=camera)
    mocker.patch.object(window_module, "get_window_spec_id", return_value=None)
    mocker.patch.object(window_module.time, "sleep")

    window_module.find_and_set_window_position(window_module.WindowSpec("Diablo IV.exe"))

    camera.reset_window_position.assert_called_once_with()


def test_resets_window_position_when_diablo_window_closes_during_geometry_lookup(window_module, mocker):
    camera = mocker.Mock()
    mocker.patch.object(window_module, "Cam", return_value=camera)
    mocker.patch.object(window_module, "get_window_spec_id", return_value=1)
    mocker.patch.object(window_module, "GetClientRect", side_effect=OSError("invalid window handle"))
    mocker.patch.object(window_module.time, "sleep")

    window_module.find_and_set_window_position(window_module.WindowSpec("Diablo IV.exe"))

    camera.reset_window_position.assert_called_once_with()
