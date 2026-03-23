import logging

from src.scripts.runtime_lifecycle import (
    refresh_language_assets,
    refresh_logging_level,
    should_notify_manual_restart,
)


class DummyDataloader:
    def __init__(self):
        self.loaded = False

    def load_data(self):
        self.loaded = True


class DummyHandler:
    def __init__(self):
        self.level = None

    def setLevel(self, level):
        self.level = level


def test_refresh_language_assets_loads_only_when_language_changes():
    dataloader = DummyDataloader()

    assert refresh_language_assets("enUS", "enUS", dataloader) == "enUS"
    assert dataloader.loaded is False

    assert refresh_language_assets("enUS", "deDE", dataloader) == "deDE"
    assert dataloader.loaded is True


def test_refresh_logging_level_updates_handlers_only_when_needed():
    logger = logging.getLogger("test_runtime_lifecycle")
    handler = DummyHandler()
    logger.handlers = [handler]

    assert refresh_logging_level("INFO", "INFO", logger) == "INFO"
    assert handler.level is None

    assert refresh_logging_level("INFO", "DEBUG", logger) == "DEBUG"
    assert handler.level == "DEBUG"


def test_should_notify_manual_restart_only_once():
    assert should_notify_manual_restart(False) is True
    assert should_notify_manual_restart(True) is False
