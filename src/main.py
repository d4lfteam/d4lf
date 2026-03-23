import ctypes
import logging
import os
import sys
from pathlib import Path

from beautifultable import BeautifulTable
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

import src.logger
from src.app_runtime import create_default_runtime
from src import __version__
from src.autoupdater import start_auto_update
from src.config.loader import IniConfigLoader
from src.runtime_checks import check_for_proper_tts_configuration

BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent

ICON_PATH = BASE_DIR / "assets" / "logo.png"

LOGGER = logging.getLogger(__name__)

# Set DPI awareness before Qt loads
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        LOGGER.exception("Failed to set DPI awareness")


def main():
    running_from_source = not getattr(sys, "frozen", False)
    if running_from_source:
        LOGGER.debug("Skipping autoupdate check as code is being run from source.")

    # --- OG D4LF STYLE HEADER (printed before other runtime logs) ---
    print(f"============ D4 Loot Filter {__version__} ============")

    table = BeautifulTable()
    table.set_style(BeautifulTable.STYLE_BOX_ROUNDED)
    table.rows.append([IniConfigLoader().advanced_options.run_vision_mode, "Run/Stop Vision Mode"])
    table.rows.append([IniConfigLoader().advanced_options.toggle_paragon_overlay, "Toggle Paragon Overlay"])

    if not IniConfigLoader().advanced_options.vision_mode_only:
        table.rows.append([IniConfigLoader().advanced_options.run_filter, "Run/Stop Auto Filter (no match = junk)"])
        table.rows.append([
            IniConfigLoader().advanced_options.run_filter_drop,
            "Run/Stop Auto Filter (no match = drop)",
        ])
        table.rows.append([
            IniConfigLoader().advanced_options.run_filter_force_refresh,
            "Force Run/Stop Filter, Resetting Item Status",
        ])
        table.rows.append([
            IniConfigLoader().advanced_options.force_refresh_only,
            "Reset Item Statuses Without A Filter After",
        ])
        table.rows.append([IniConfigLoader().advanced_options.move_to_inv, "Move Items From Chest To Inventory"])
        table.rows.append([IniConfigLoader().advanced_options.move_to_chest, "Move Items From Inventory To Chest"])

    table.rows.append([IniConfigLoader().advanced_options.exit_key, "Exit"])
    table.columns.header = ["hotkey", "action"]

    print(table)
    print()  # blank line, just like OG D4LF
    # --- END HEADER ---

    if IniConfigLoader().advanced_options.vision_mode_only:
        LOGGER.info("Vision mode only is enabled. All functionality that clicks the screen is disabled.")

    runtime = create_default_runtime(tts_validator=check_for_proper_tts_configuration)
    runtime.start_runtime(running_from_source=running_from_source)


def hide_console():
    """Hide the console window (Windows only)."""
    if sys.platform == "win32":
        ctypes.windll.user32.ShowWindow(
            ctypes.windll.kernel32.GetConsoleWindow(),
            0,  # SW_HIDE
        )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--autoupdate":
        src.logger.setup(log_level=IniConfigLoader().advanced_options.log_lvl.value, enable_stdout=True)
        start_auto_update()

    elif len(sys.argv) > 1 and sys.argv[1] == "--autoupdatepost":
        src.logger.setup(log_level=IniConfigLoader().advanced_options.log_lvl.value, enable_stdout=True)
        start_auto_update(postprocess=True)

    elif len(sys.argv) > 1 and sys.argv[1] == "--consoleonly":
        # Console-only mode: keep console visible
        src.logger.setup(log_level=IniConfigLoader().advanced_options.log_lvl.value, enable_stdout=True)
        main()

    else:
        # Enable stdout logging when running from source (for IDE terminal), hide console for compiled exe
        running_from_source = not getattr(sys, "frozen", False)
        if not running_from_source:
            hide_console()
        os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
        src.logger.setup(log_level=IniConfigLoader().advanced_options.log_lvl.value, enable_stdout=running_from_source)

        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon(str(ICON_PATH)))
        # Has to be imported in line to avoid circular reference
        from src.gui.unified_window import UnifiedMainWindow

        window = UnifiedMainWindow()
        window.show()
        sys.exit(app.exec())
