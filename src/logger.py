from __future__ import annotations

import datetime
import logging
import logging.handlers
import sys
import threading
from typing import TYPE_CHECKING

import colorama

from src import __version__
from src.config import BASE_DIR

if TYPE_CHECKING:
    from collections.abc import Container

logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

LOGGER = logging.getLogger(__name__)

LOG_DIR = BASE_DIR / "logs"

_setup_called = False
_startup_buffer_handler: logging.Handler | None = None
_startup_log_records: list[logging.LogRecord] = []


class _StartupBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        _startup_log_records.append(record)


class ColoredFormatter(logging.Formatter):
    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: str = "%",
        validate: bool = True,
        *,
        defaults: dict[str, object] | None = None,
    ) -> None:
        colorama.just_fix_windows_console()
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate, defaults=defaults)

    COLORS = {
        "DEBUG": colorama.Fore.LIGHTCYAN_EX,
        "INFO": colorama.Fore.GREEN,
        "WARNING": colorama.Fore.YELLOW,
        "ERROR": colorama.Fore.RED,
        "CRITICAL": colorama.Fore.MAGENTA + colorama.Back.YELLOW,
    }

    def format(self, record: logging.LogRecord) -> str:
        log_message = super().format(record)
        return self.COLORS.get(record.levelname, "") + log_message + colorama.Style.RESET_ALL


def create_formatter(colored: bool = False, technical: bool = False, timestamp: bool = False) -> logging.Formatter:
    parts = []
    if timestamp:
        parts.append("%(asctime)s")
    if technical:
        parts.extend(["%(threadName)s", "%(levelname)s", "%(name)s:%(lineno)d"])

    fmt = " | ".join(parts) + " | %(message)s" if parts else "%(message)s"
    if colored:
        return ColoredFormatter(fmt)
    return logging.Formatter(fmt)


def apply_log_level(
    log_level: str, *, skip_handler_names: Container[str] = (), formatter: logging.Formatter | None = None
) -> None:
    """Apply a new log level to the root logger and its handlers at runtime.

    Args:
        log_level: The new level name (case-insensitive), e.g. "DEBUG" or "INFO".
        skip_handler_names: Names of handlers to leave untouched.
        formatter: Formatter to apply to changed handlers.
    """
    level = log_level.upper()
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    for handler in root_logger.handlers:
        if getattr(handler, "name", "") in skip_handler_names:
            continue
        handler.setLevel(level)
        if formatter is not None:
            handler.setFormatter(formatter)


def setup(
    log_level: str = "DEBUG",
    *,
    enable_stdout: bool = True,
    technical: bool = False,
    timestamp: bool = False,
    buffer_startup: bool = False,
) -> None:
    LOG_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger()
    threading.excepthook = _log_unhandled_exceptions
    if buffer_startup:
        _enable_startup_buffer(logger)

    # File handler: Always DEBUG level and always includes technical info
    log_timestamp = datetime.datetime.now(tz=datetime.UTC).strftime("%Y_%m_%d_%H_%M_%S")
    rotating_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / f"log_{log_timestamp}.log", mode="a", maxBytes=10 * 1024**2, backupCount=1000, encoding="utf8"
    )
    rotating_handler.set_name("D4LF_FILE")
    rotating_handler.setLevel(logging.DEBUG)
    rotating_handler.setFormatter(create_formatter(colored=False, technical=True, timestamp=True))
    logger.addHandler(rotating_handler)

    # create StreamHandler for console output (optional)
    if enable_stdout:
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.set_name("D4LF_CONSOLE")
        stream_handler.setLevel(log_level.upper())
        stream_handler.setFormatter(create_formatter(colored=True, technical=technical, timestamp=timestamp))
        logger.addHandler(stream_handler)

    # Set default log level for root logger
    logger.setLevel("DEBUG")

    global _setup_called
    if not _setup_called:
        LOGGER.info(f"Running version v{__version__}")
        _setup_called = True

    # Clean up old log files
    clean_up_old_log_files()


def _enable_startup_buffer(logger: logging.Logger) -> None:
    global _startup_buffer_handler
    if _startup_buffer_handler is not None:
        return
    _startup_buffer_handler = _StartupBufferHandler()
    _startup_buffer_handler.set_name("D4LF_STARTUP_BUFFER")
    _startup_buffer_handler.setLevel(logging.DEBUG)
    logger.addHandler(_startup_buffer_handler)


def consume_startup_log_records() -> list[logging.LogRecord]:
    global _startup_buffer_handler
    logger = logging.getLogger()
    if _startup_buffer_handler is not None:
        logger.removeHandler(_startup_buffer_handler)
        _startup_buffer_handler = None
    records = _startup_log_records.copy()
    _startup_log_records.clear()
    return records


def clean_up_old_log_files():
    max_to_keep = 10

    files = [f for f in LOG_DIR.iterdir() if f.is_file() and f.name.startswith("log_")]
    sorted_files = sorted(files, key=lambda f: f.stat().st_mtime)  # Oldest first
    files_to_delete = sorted_files[:-max_to_keep] if len(sorted_files) > max_to_keep else []

    for file in files_to_delete:
        file.unlink()
        LOGGER.debug(f"Cleaned up old log file: {file}")


def _log_unhandled_exceptions(args: threading.ExceptHookArgs) -> None:
    if isinstance(args.exc_value, SystemExit):
        return
    thread_name = args.thread.name if args.thread is not None else "unknown"
    LOGGER.critical(
        "Unhandled exception caused by thread '%s'",
        thread_name,
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
