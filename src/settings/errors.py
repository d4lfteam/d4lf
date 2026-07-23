"""Settings load failure values and reporting helpers."""

import logging
from collections.abc import Callable
from pathlib import Path

LOGGER = logging.getLogger("src.settings.loader")


class SettingsLoadError(RuntimeError):
    """A settings document could not be parsed or validated."""

    def __init__(self, config_path: Path, error: Exception, *, log_path: Path | None = None) -> None:
        self.config_path = config_path
        self.log_path = log_path or Path(__file__).parents[2] / "logs"
        self.original = error
        super().__init__(f"Unable to load settings from {config_path}: {error}")


ConfigLoadErrorListener = Callable[[SettingsLoadError], None]


def log_load_error(error: SettingsLoadError) -> None:
    LOGGER.error("Failed to load settings from %s", error.config_path, exc_info=error.original)


def make_cleanup_record(logger: logging.Logger, message: str, args: tuple[object, ...]) -> logging.LogRecord:
    path_name, line_number, _, _ = logger.findCaller(stacklevel=3)
    return logger.makeRecord(logger.name, logging.WARNING, path_name, line_number, message, args, None)
