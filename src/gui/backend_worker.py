import logging
import sys
import time
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

from src.autoupdater import notify_if_update
from src.settings import get_settings

if TYPE_CHECKING:
    from src.scripts.handler import ScriptHandler

if sys.platform == "win32":
    from src import perception as perception_module
    from src.item import Filter
    from src.main import check_for_proper_tts_configuration
    from src.overlay import Overlay
    from src.perception import game_window_ready
    from src.scripts.handler import ScriptHandler
    from src.utils.window import WindowSpec, start_detecting_window
else:
    perception_module = None

LOGGER = logging.getLogger(__name__)


class BackendWorker(QObject):
    finished = pyqtSignal()
    script_handler: ScriptHandler | None = None

    def run(self):
        if sys.platform != "win32":
            LOGGER.info("GUI-only mode is active on non-Windows. Backend runtime is disabled.")
            self.finished.emit()
            return

        Filter().load_files()

        running_from_source = not getattr(sys, "frozen", False)
        if running_from_source:
            LOGGER.debug("Skipping autoupdate check as code is being run from source.")
        else:
            notify_if_update()

        win_spec = WindowSpec(get_settings().advanced_options.process_name)
        start_detecting_window(win_spec)

        while not game_window_ready():
            time.sleep(0.2)

        time.sleep(0.5)
        self.script_handler = ScriptHandler()
        check_for_proper_tts_configuration()
        perception_module.start_connection()
        Overlay().run()
        self.finished.emit()
