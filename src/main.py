"""Executable entry point for D4LF."""

import ctypes
import logging
import os
import sys

from beautifultable import BeautifulTable, Style
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

import src.logger
from src import __version__
from src.app import (
    ICON_PATH,
    SETUP_INSTRUCTIONS_URL,
    check_for_proper_tts_configuration,
    get_d4_local_prefs_file,
    prepare_runtime_directories,
    show_settings_load_error,
)
from src.autoupdater import start_auto_update
from src.settings import Settings, SettingsLoadError, get_settings

LOGGER = logging.getLogger(__name__)

__all__ = [
    "SETUP_INSTRUCTIONS_URL",
    "check_for_proper_tts_configuration",
    "get_d4_local_prefs_file",
    "hide_console",
    "main",
    "run",
]

if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except AttributeError:
        ctypes.windll.user32.SetProcessDPIAware()


def main() -> None:
    """Prepare application state and run the configured backend."""
    if sys.platform != "win32":
        LOGGER.info("Running in GUI-only mode on non-Windows. Runtime backend (TTS/automation) is disabled.")
        return

    prepare_runtime_directories()
    from src.app.backend import run_backend  # ruff:ignore[import-outside-top-level]

    settings = get_settings()
    adv = settings.advanced_options
    LOGGER.info("============ D4 Loot Filter %s ============", __version__)

    table = BeautifulTable()
    table.set_style(Style.STYLE_BOX_ROUNDED)
    rows = [
        (adv.run_vision_mode, "Run/Stop Vision Mode"),
        (adv.info_overlay, "Info Panel Overlay"),
        (adv.toggle_paragon_overlay, "Toggle Paragon Overlay"),
    ]
    if not adv.vision_mode_only:
        rows.extend([
            (adv.run_filter, "Run/Stop Auto Filter (no match = junk)"),
            (adv.run_filter_drop, "Run/Stop Auto Filter (no match = drop)"),
            (adv.run_filter_force_refresh, "Force Run/Stop Filter, Resetting Item Status"),
            (adv.force_refresh_only, "Reset Item Statuses Without A Filter After"),
            (adv.move_to_inv, "Move Items From Chest To Inventory"),
            (adv.move_to_chest, "Move Items From Inventory To Chest"),
        ])
    rows.append((adv.exit_key, "Exit"))
    for row in rows:
        table.rows.append(row)
    table.columns.header = ["hotkey", "action"]
    for line in str(table).splitlines():
        LOGGER.info(line)

    if adv.vision_mode_only:
        LOGGER.info("Vision mode only is enabled. All functionality that clicks the screen is disabled.")
    LOGGER.debug("Vision mode type: %s", settings.general.vision_mode_type.value)
    run_backend()


def hide_console() -> None:
    """Hide the console window (Windows only)."""
    if sys.platform == "win32":
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)


def _configure_logging(*, stdout: bool, buffer_startup: bool = False) -> Settings:
    if not src.logger.is_configured():
        src.logger.setup(log_level="DEBUG", enable_stdout=stdout, buffer_startup=buffer_startup)
    settings = get_settings()
    _apply_configured_logging(settings)
    return settings


def _apply_configured_logging(settings: Settings) -> None:
    """Apply validated settings to handlers created during early startup."""
    advanced_options = settings.advanced_options
    formatter = src.logger.create_formatter(
        colored=True, technical=advanced_options.technical_log_info, timestamp=advanced_options.log_timestamp
    )
    src.logger.apply_log_level(advanced_options.log_lvl.value, skip_handler_names={"D4LF_FILE"}, formatter=formatter)


def run() -> int:
    """Dispatch CLI update modes and start the Qt shell."""
    if len(sys.argv) > 1 and sys.argv[1] == "--autoupdate":
        try:
            _configure_logging(stdout=True)
        except SettingsLoadError as error:
            print(f"Could not load {error.config_path}; see {error.log_path} for details.", file=sys.stderr)
            return 1
        start_auto_update()
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "--autoupdatepost":
        try:
            _configure_logging(stdout=True)
        except SettingsLoadError as error:
            print(f"Could not load {error.config_path}; see {error.log_path} for details.", file=sys.stderr)
            return 1
        start_auto_update(postprocess=True)
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "--consoleonly":
        try:
            _configure_logging(stdout=True)
        except SettingsLoadError as error:
            print(f"Could not load {error.config_path}; see {error.log_path} for details.", file=sys.stderr)
            return 1
        main()
        return 0

    running_from_source = not getattr(sys, "frozen", False)
    try:
        _configure_logging(stdout=running_from_source, buffer_startup=True)
    except SettingsLoadError as error:
        app = QApplication.instance() or QApplication(sys.argv)
        show_settings_load_error(error)
        return 1

    if not running_from_source:
        hide_console()
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    from src.app.shell import UnifiedMainWindow  # ruff:ignore[import-outside-top-level]

    window = UnifiedMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
