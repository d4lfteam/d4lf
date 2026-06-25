import logging

import pytest

from src.logger import apply_log_level, create_formatter


@pytest.fixture
def isolated_root_logger():
    root_logger = logging.getLogger()
    original_level = root_logger.level
    original_handlers = root_logger.handlers[:]
    root_logger.handlers = []
    try:
        yield root_logger
    finally:
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)


def _make_handler(name: str, level: int) -> logging.Handler:
    handler = logging.NullHandler()
    handler.name = name
    handler.setLevel(level)
    return handler


def test_apply_log_level_updates_root_and_handlers(isolated_root_logger):
    file_handler = _make_handler("D4LF_FILE", logging.INFO)
    console_handler = _make_handler("QT_CONSOLE", logging.INFO)
    isolated_root_logger.addHandler(file_handler)
    isolated_root_logger.addHandler(console_handler)

    apply_log_level("debug")

    assert isolated_root_logger.level == logging.DEBUG
    assert file_handler.level == logging.DEBUG
    assert console_handler.level == logging.DEBUG


def test_apply_log_level_skips_named_handlers(isolated_root_logger):
    console_handler = _make_handler("QT_CONSOLE", logging.DEBUG)
    activity_handler = _make_handler("QT_ACTIVITY", logging.INFO)
    isolated_root_logger.addHandler(console_handler)
    isolated_root_logger.addHandler(activity_handler)

    apply_log_level("ERROR", skip_handler_names={"QT_ACTIVITY"})

    assert console_handler.level == logging.ERROR
    assert activity_handler.level == logging.INFO


def test_apply_log_level_is_case_insensitive(isolated_root_logger):
    handler = _make_handler("D4LF_FILE", logging.ERROR)
    isolated_root_logger.addHandler(handler)

    apply_log_level("info")

    assert handler.level == logging.INFO


def _record() -> logging.LogRecord:
    return logging.LogRecord(
        name="src.item.filter",
        level=logging.INFO,
        pathname=__file__,
        lineno=556,
        msg="item marked junk",
        args=(),
        exc_info=None,
    )


def test_default_gui_log_formatter_hides_technical_information_and_timestamp():
    assert create_formatter(technical=False, timestamp=False).format(_record()) == "item marked junk"


def test_technical_gui_log_formatter_restores_technical_information():
    formatted = create_formatter(technical=True, timestamp=False).format(_record())

    assert formatted.endswith(" | INFO | src.item.filter:556 | item marked junk")


def test_timestamp_gui_log_formatter_restores_timestamp():
    formatted = create_formatter(technical=False, timestamp=True).format(_record())

    assert formatted.endswith(" | item marked junk")
    assert formatted != "item marked junk"
