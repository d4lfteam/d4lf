import tesserocr  # noqa #  Note: Somehow needed, otherwise the binary has an issue with tesserocr
from PIL import Image  # noqa #  Note: Somehow needed, otherwise the binary has an issue with tesserocr
import logging
import os
import sys
import time
import traceback

import keyboard
from beautifultable import BeautifulTable

import src.logger
from src import __version__
from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import ItemRefreshType
from src.gui.qt_gui import start_gui
from src.item.filter import Filter
from src.logger import LOG_DIR
from src.overlay import Overlay
from src.utils.process_handler import safe_exit
from src.utils.window import WindowSpec, start_detecting_window

LOGGER = logging.getLogger(__name__)


def main():
    # Create folders for logging stuff
    for dir_name in [LOG_DIR / "screenshots", IniConfigLoader().user_dir, IniConfigLoader().user_dir / "profiles"]:
        os.makedirs(dir_name, exist_ok=True)

    LOGGER.info(f"Adapt your configs via gui.bat or directly in: {IniConfigLoader().user_dir}")

    if IniConfigLoader().advanced_options.vision_mode_only:
        LOGGER.info("Vision mode only is enabled. All functionality that clicks the screen is disabled.")

    Filter().load_files()

    print(f"============ D4 Loot Filter {__version__} ============")
    table = BeautifulTable()
    table.set_style(BeautifulTable.STYLE_BOX_ROUNDED)
    table.rows.append([IniConfigLoader().advanced_options.run_scripts, "Run/Stop Vision Filter"])
    if not IniConfigLoader().advanced_options.vision_mode_only:
        table.rows.append([IniConfigLoader().advanced_options.run_filter, "Run/Stop Auto Filter"])
        table.rows.append([IniConfigLoader().advanced_options.run_filter_force_refresh, "Force Run/Stop Filter, Resetting Item Status"])
        table.rows.append([IniConfigLoader().advanced_options.force_refresh_only, "Reset Item Statuses Without A Filter After"])
        table.rows.append([IniConfigLoader().advanced_options.move_to_inv, "Move Items From Chest To Inventory"])
        table.rows.append([IniConfigLoader().advanced_options.move_to_chest, "Move Items From Inventory To Chest"])
    table.rows.append([IniConfigLoader().advanced_options.exit_key, "Exit"])
    table.columns.header = ["hotkey", "action"]
    print(table)
    print("\n")

    win_spec = WindowSpec(IniConfigLoader().advanced_options.process_name)
    start_detecting_window(win_spec)
    while not Cam().is_offset_set():
        time.sleep(0.2)

    overlay = None

    keyboard.add_hotkey(IniConfigLoader().advanced_options.run_scripts, lambda: overlay.run_scripts() if overlay is not None else None)
    keyboard.add_hotkey(IniConfigLoader().advanced_options.exit_key, lambda: safe_exit())
    if not IniConfigLoader().advanced_options.vision_mode_only:
        keyboard.add_hotkey(IniConfigLoader().advanced_options.run_filter, lambda: overlay.filter_items() if overlay is not None else None)
        keyboard.add_hotkey(
            IniConfigLoader().advanced_options.run_filter_force_refresh,
            lambda: overlay.filter_items(ItemRefreshType.force_with_filter) if overlay is not None else None,
        )
        keyboard.add_hotkey(
            IniConfigLoader().advanced_options.force_refresh_only,
            lambda: overlay.filter_items(ItemRefreshType.force_without_filter) if overlay is not None else None,
        )
        keyboard.add_hotkey(IniConfigLoader().advanced_options.move_to_inv, lambda: overlay.move_items_to_inventory())
        keyboard.add_hotkey(IniConfigLoader().advanced_options.move_to_chest, lambda: overlay.move_items_to_stash())

    overlay = Overlay()
    overlay.run()


if __name__ == "__main__":
    src.logger.setup(log_level=IniConfigLoader().advanced_options.log_lvl.value)
    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        start_gui()
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("Press Enter to exit ...")
        input()
