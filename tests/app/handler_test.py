from unittest.mock import Mock

from src.app.handler import ScriptHandler


def test_loot_interaction_stops_and_restarts_running_vision_mode():
    handler = object.__new__(ScriptHandler)
    handler.loot_interaction_thread = object()
    handler.did_stop_scripts = False
    handler.run_vision_mode = Mock()

    class VisionMode:
        def __init__(self):
            self.stopped = False

        def running(self):
            return not self.stopped

        def stop(self):
            self.stopped = True

    handler.vision_mode = VisionMode()
    action = Mock()

    handler._wrapper_run_loot_interaction_method(action)

    action.assert_called_once_with()
    handler.run_vision_mode.assert_called_once_with()
    assert handler.loot_interaction_thread is None
