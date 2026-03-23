from __future__ import annotations

import logging


def refresh_language_assets(current_language: str, new_language: str, dataloader) -> str:
    if new_language == current_language:
        return current_language

    dataloader.load_data()
    return new_language


def refresh_logging_level(current_log_level: str, new_log_level: str, root_logger: logging.Logger) -> str:
    if new_log_level == current_log_level:
        return current_log_level

    for handler in root_logger.handlers:
        handler.setLevel(new_log_level)
    return new_log_level


def should_notify_manual_restart(already_warned: bool) -> bool:
    return not already_warned
