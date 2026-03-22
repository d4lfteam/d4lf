import logging

from src.gui.importer.gui_common import log_import_summary


def test_log_import_summary_logs_finished_message(caplog):
    logger = logging.getLogger("tests.gui.importer.finished")

    with caplog.at_level(logging.INFO, logger=logger.name):
        log_import_summary(logger, "D4Builds", ["profile_one", "profile_two"])

    assert "Finished importing 2 D4Builds profile(s)" in caplog.text


def test_log_import_summary_logs_empty_warning(caplog):
    logger = logging.getLogger("tests.gui.importer.empty")

    with caplog.at_level(logging.WARNING, logger=logger.name):
        log_import_summary(logger, "Maxroll", [])

    assert "No Maxroll profiles were imported" in caplog.text
