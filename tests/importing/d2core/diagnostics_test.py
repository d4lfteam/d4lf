import logging

from src.importing.d2core.diagnostics import D2CoreWarningSink


def test_warning_sink_deduplicates_by_current_variant_but_logs_display_name(caplog) -> None:
    logger = logging.getLogger("d2core-test")
    sink = D2CoreWarningSink(logger=logger)
    sink.set_variant("2")
    caplog.set_level(logging.WARNING, logger="d2core-test")

    sink.warn("D2C-W110", "Readable Variant", "equipment", "affix-key")
    sink.warn("D2C-W110", "Another Label", "equipment", "affix-key")

    assert sink.count == 1
    assert caplog.messages == ["D2C-W110 d2core import degraded (Readable Variant equipment affix-key)"]
