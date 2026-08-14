"""Windows backend composition used by the desktop shell."""

import logging
import sys
import time

from PyQt6.QtCore import QObject, pyqtSignal

from src.autoupdater import notify_if_update
from src.settings import get_settings

if sys.platform == "win32":
    from src import perception as _perception
    from src.app.handler import ScriptHandler
    from src.automation import WindowSpec, start_detecting_window
    from src.item.filter import Filter
    from src.overlay import Overlay
    from src.perception import game_window_ready
else:
    _perception = None

from typing import TYPE_CHECKING

from src.app.startup import check_for_proper_tts_configuration

if TYPE_CHECKING:
    from types import ModuleType

LOGGER = logging.getLogger(__name__)


def get_perception_module() -> ModuleType | None:
    """Return the active perception adapter, or ``None`` in GUI-only mode."""
    return _perception


class BackendWorker(QObject):
    """Own the game-facing runtime and expose its lifecycle to the Qt shell."""

    finished = pyqtSignal()
    script_handler = None

    def run(self) -> None:
        if sys.platform != "win32":
            LOGGER.info("GUI-only mode is active on non-Windows. Backend runtime is disabled.")
            self.finished.emit()
            return

        _perception.start_connection()
        Filter().load_files()
        if getattr(sys, "frozen", False):
            notify_if_update()
        else:
            LOGGER.debug("Skipping autoupdate check as code is being run from source.")

        win_spec = WindowSpec(get_settings().advanced_options.process_name)
        start_detecting_window(win_spec)
        while not game_window_ready():
            time.sleep(0.2)
        time.sleep(0.5)

        self.script_handler = ScriptHandler()
        check_for_proper_tts_configuration()
        Overlay().run()
        self.finished.emit()


def run_backend() -> None:
    """Run the game backend synchronously for the console-only entry point."""
    worker = BackendWorker()
    worker.run()
