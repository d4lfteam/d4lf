from __future__ import annotations

import datetime
import logging
import logging.handlers
import sys
import threading
import typing

import colorama

from src import __version__
from src.config import BASE_DIR

logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

LOGGER = logging.getLogger(__name__)

LOG_DIR = BASE_DIR / "logs"

class ThreadNameFilter(logging.Filter):
    def filter(self, record):
        if record.threadName.startswith("Dummy-"):
            record.threadName = record.threadName.replace("Dummy-", "Thread-")
        return True

class ColoredFormatter(logging.Formatter):
    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: str = "%",
        validate: bool = True,
        *,
        defaults: dict[str, typing.Any] | None = None,
    ) -> None:
        colorama.just_fix_windows_console()
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate, defaults=defaults)

    COLORS = {
        "DEBUG": colorama.Fore.BLUE,
        "INFO": colorama.Fore.GREEN,
        "WARNING": colorama.Fore.YELLOW,
        "ERROR": colorama.Fore.RED,
        "CRITICAL": colorama.Fore.MAGENTA + colorama.Back.YELLOW,
    }

    def format(self, record: logging.LogRecord) -> str:
        log_message = super().format(record)
        return self.COLORS.get(record.levelname, "") + log_message + colorama.Style.RESET_ALL


def _setup_log_filename(fmt: str) -> str:
    current_datetime = datetime.datetime.now(tz=datetime.UTC)

    filename = fmt.format(date=current_datetime.strftime("%Y-%m-%d"), time=current_datetime.strftime("%H-%M-%S"))
    if filename and not filename.lower().endswith(".log"):
        filename += ".log"
    return filename


def create_formatter(colored=False):
    fmt = "%(asctime)s | %(threadName)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s"
    if colored:
        return ColoredFormatter(fmt)
    return logging.Formatter(fmt)


def setup(log_level: str = "DEBUG", *, enable_stdout: bool = True) -> None:
    LOG_DIR.mkdir(exist_ok=True)

    LOGGER.debug(f"LOG_PATH: {LOG_DIR}")
    logger = logging.getLogger()
    threading.excepthook = _log_unhandled_exceptions
    # create rotating file handler
    rotating_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / f"log_{datetime.datetime.now(tz=datetime.UTC).strftime('%Y_%m_%d_%H_%M_%S')}.txt",
        mode="w",
        maxBytes=10 * 1024**2,
        backupCount=1000,
        encoding="utf8",
    )
    rotating_handler.set_name("D4LF_FILE")
    rotating_handler.setLevel(log_level.upper())

    # create StreamHandler for console output (optional)
    if enable_stdout:
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.addFilter(ThreadNameFilter())
        stream_handler.set_name("D4LF_CONSOLE")
        stream_handler.setLevel(log_level.upper())
        stream_handler.setFormatter(create_formatter(colored=True))
        logger.addHandler(stream_handler)

    rotating_handler.setFormatter(create_formatter(colored=False))

    # add rotating file handler
    logger.addHandler(rotating_handler)

    # Set default log level for root logger
    logger.setLevel("DEBUG")
    LOGGER.info(f"Running version v{__version__}")


def _log_unhandled_exceptions(args: typing.Any) -> None:
    if len(args) >= 2 and isinstance(args[1], SystemExit):
        return
    LOGGER.critical(
        f"Unhandled exception caused by thread '{args.thread.name}'",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
