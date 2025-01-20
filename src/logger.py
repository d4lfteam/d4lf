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
    if not filename.lower().endswith(".log") and filename != "":
        filename += ".log"
    return filename


def create_formatter(colored: bool) -> logging.Formatter:
    """Create a formatter for logging.

    :param colored: If true, use colors in output
    :return: the logging formatter
    """
    # log_format = "%(asctime)s.%(msecs)03d | %(processName)s | %(threadName)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s"
    log_format = "%(asctime)s.%(msecs)03d | %(threadName)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s"
    date_format = "%Y-%m-%d | %H:%M:%S"
    if colored:
        return ColoredFormatter(fmt=log_format, datefmt=date_format)
    return logging.Formatter(fmt=log_format, datefmt=date_format)


def setup(log_level: str = "DEBUG") -> None:
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
    # create StreamHandler for console output
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.set_name("D4LF_CONSOLE")
    stream_handler.setLevel(log_level.upper())
    # create and set custom log formatter
    stream_handler.setFormatter(create_formatter(colored=True))
    rotating_handler.setFormatter(create_formatter(colored=False))
    # add new handlers to logger
    logger.addHandler(stream_handler)
    logger.addHandler(rotating_handler)
    # Set default log level for root logger. Python will pick the highest level out of root logger and handler
    logger.setLevel("DEBUG")
    LOGGER.info(f"Running version v{__version__}")


def _log_unhandled_exceptions(args: typing.Any) -> None:
    if len(args) >= 2 and isinstance(args[1], SystemExit):
        return
    LOGGER.critical(
        f"Unhandled exception caused by thread '{args.thread.name}'", exc_info=(args.exc_type, args.exc_value, args.exc_traceback)
    )
