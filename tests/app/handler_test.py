import threading
import typing

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

from src.app.handler import ScriptHandler


def test_loot_interaction_stops_and_restarts_running_vision_mode(mocker: MockerFixture) -> None:
    handler = object.__new__(ScriptHandler)
    handler.loot_interaction_thread = threading.Thread()
    handler.did_stop_scripts = False
    handler.run_vision_mode = mocker.Mock()

    class VisionMode:
        def __init__(self) -> None:
            self.stopped = False

        def running(self) -> bool:
            return not self.stopped

        def stop(self) -> None:
            self.stopped = True

        def start(self) -> None:
            self.stopped = False

    handler.vision_mode = VisionMode()
    action = mocker.Mock()

    handler._wrapper_run_loot_interaction_method(action)

    action.assert_called_once_with()
    handler.run_vision_mode.assert_called_once_with()
    assert handler.loot_interaction_thread is None
