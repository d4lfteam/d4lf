import logging
import typing
from typing import override
from unittest.mock import Mock

if typing.TYPE_CHECKING:
    import tkinter as tk

    import pytest

import src.loot.vision_mode as vision_mode_module
from src.loot.vision_mode import VisionMode, create_on_ui_thread


class _RecordingMode(VisionMode[str]):
    def __init__(self, root: tk.Toplevel, canvas: tk.Canvas) -> None:
        super().__init__(root, canvas)
        self.events: list[str] = []
        self.fail = False

    @override
    def draw(self, command: str) -> None:
        if self.fail:
            message = "boom"
            raise RuntimeError(message)
        self.events.append(f"draw {command}")

    @override
    def on_tts(self, _: list[str]) -> None:
        self.events.append("tts")

    @override
    def on_stop(self) -> None:
        self.events.append("stop")


def test_start_subscribes_to_item_events(monkeypatch) -> None:
    publisher = Mock()
    monkeypatch.setattr(vision_mode_module, "Publisher", Mock(return_value=publisher))
    mode = _RecordingMode(Mock(), Mock())

    mode.start()

    assert mode.running()
    publisher.subscribe_item.assert_called_once_with(mode.on_tts)


def test_stop_cleans_up_before_unsubscribing(monkeypatch) -> None:
    publisher = Mock()
    mode = _RecordingMode(Mock(), Mock())
    publisher.unsubscribe_item.side_effect = lambda _callback: mode.events.append("unsubscribe")
    monkeypatch.setattr(vision_mode_module, "Publisher", Mock(return_value=publisher))
    mode.start()

    mode.stop()

    assert not mode.running()
    assert mode.events == ["stop", "unsubscribe"]
    publisher.unsubscribe_item.assert_called_once_with(mode.on_tts)


def test_draw_from_queue_draws_submitted_commands_in_order() -> None:
    canvas = Mock()
    mode = _RecordingMode(Mock(), canvas)
    canvas.after.reset_mock()

    mode.submit("first")
    mode.submit("second")
    for _ in range(3):
        mode.draw_from_queue()

    assert mode.events == ["draw first", "draw second"]
    canvas.after.assert_called_with(10, mode.draw_from_queue)


def test_draw_from_queue_reschedules_and_logs_when_drawing_fails(caplog: pytest.LogCaptureFixture) -> None:
    canvas = Mock()
    mode = _RecordingMode(Mock(), canvas)
    canvas.after.reset_mock()
    mode.fail = True
    mode.submit("first")

    with caplog.at_level(logging.ERROR, logger="src.loot.vision_mode"):
        mode.draw_from_queue()

    canvas.after.assert_called_once_with(10, mode.draw_from_queue)
    assert "Error while drawing vision mode overlay" in caplog.text
    assert "boom" in caplog.text


def test_draw_from_queue_reschedules_when_queue_is_empty() -> None:
    canvas = Mock()
    mode = _RecordingMode(Mock(), canvas)
    canvas.after.reset_mock()

    mode.draw_from_queue()

    canvas.after.assert_called_once_with(10, mode.draw_from_queue)
    assert mode.events == []


def test_create_on_ui_thread_builds_mode_with_overlay_window_and_schedules_draw_loop(monkeypatch) -> None:
    root, canvas, parent = Mock(), Mock(), Mock()
    create_overlay_toplevel = Mock(return_value=(root, canvas))
    monkeypatch.setattr(vision_mode_module, "call_on_ui_thread", lambda fn: fn())
    monkeypatch.setattr(vision_mode_module, "create_overlay_toplevel", create_overlay_toplevel)
    monkeypatch.setattr(vision_mode_module, "get_root", Mock(return_value=parent))

    mode = create_on_ui_thread(_RecordingMode)

    create_overlay_toplevel.assert_called_once_with(parent)
    assert mode.root is root
    assert mode.canvas is canvas
    canvas.after.assert_called_once_with(0, mode.draw_from_queue)
