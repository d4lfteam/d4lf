from __future__ import annotations

from pathlib import Path
from typing import Any


class AppRuntime:
    def __init__(
        self,
        *,
        config_loader,
        filter_loader,
        cam,
        tts_module,
        overlay_factory,
        script_handler_factory,
        window_detector,
        window_spec_factory,
        update_notifier,
        tts_validator,
        ensure_dirs,
        log_dir: Path,
        sleep,
    ) -> None:
        self._config = config_loader
        self._filter_loader = filter_loader
        self._cam = cam
        self._tts = tts_module
        self._overlay_factory = overlay_factory
        self._script_handler_factory = script_handler_factory
        self._window_detector = window_detector
        self._window_spec_factory = window_spec_factory
        self._update_notifier = update_notifier
        self._tts_validator = tts_validator
        self._ensure_dirs = ensure_dirs
        self._log_dir = log_dir
        self._sleep = sleep

    def prepare_environment(self) -> None:
        self._ensure_dirs(self._log_dir / "screenshots", self._config.user_dir, self._config.user_dir / "profiles")
        self._filter_loader.load_files()

    def maybe_notify_update(self, *, running_from_source: bool) -> None:
        if not running_from_source:
            self._update_notifier()

    def wait_for_window_ready(self) -> None:
        win_spec = self._window_spec_factory(self._config.advanced_options.process_name)
        self._window_detector(win_spec)
        while not self._cam.is_offset_set():
            self._sleep(0.2)
        self._sleep(0.5)

    def start_runtime(self, *, running_from_source: bool) -> Any:
        self.prepare_environment()
        self.maybe_notify_update(running_from_source=running_from_source)
        self.wait_for_window_ready()
        self._script_handler_factory()
        self._tts_validator()
        self._tts.start_connection()
        overlay = self._overlay_factory()
        overlay.run()
        return overlay


def create_default_runtime(*, tts_validator) -> AppRuntime:
    import time

    from src import tts
    from src.autoupdater import notify_if_update
    from src.bootstrap import ensure_runtime_dirs
    from src.cam import Cam
    from src.config.loader import IniConfigLoader
    from src.item.filter import Filter
    from src.logger import LOG_DIR
    from src.overlay import Overlay
    from src.scripts.handler import ScriptHandler
    from src.utils.window import WindowSpec, start_detecting_window

    return AppRuntime(
        config_loader=IniConfigLoader(),
        filter_loader=Filter(),
        cam=Cam(),
        tts_module=tts,
        overlay_factory=Overlay,
        script_handler_factory=ScriptHandler,
        window_detector=start_detecting_window,
        window_spec_factory=WindowSpec,
        update_notifier=notify_if_update,
        tts_validator=tts_validator,
        ensure_dirs=ensure_runtime_dirs,
        log_dir=LOG_DIR,
        sleep=time.sleep,
    )
