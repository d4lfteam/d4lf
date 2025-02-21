import logging
import os
import pathlib
import sys
import time
import traceback
from pathlib import Path

import psutil
import tesserocr  # noqa #  Note: Somehow needed, otherwise the binary has an issue with tesserocr
from beautifultable import BeautifulTable
from PIL import Image  # noqa #  Note: Somehow needed, otherwise the binary has an issue with tesserocr

import src.logger
from src import __version__, tts
from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import UseTTSType
from src.gui.qt_gui import start_gui
from src.item.filter import Filter
from src.logger import LOG_DIR
from src.overlay import Overlay
from src.scripts.common import SETUP_INSTRUCTIONS_URL
from src.scripts.handler import ScriptHandler
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

    ScriptHandler()

    if IniConfigLoader().general.use_tts in [UseTTSType.full, UseTTSType.mixed]:
        LOGGER.debug(f"TTS mode: {IniConfigLoader().general.use_tts.value}")
        check_for_proper_tts_configuration()
        tts.start_connection()

    overlay = Overlay()
    overlay.run()


def check_for_proper_tts_configuration():
    # Check that the dll has been installed
    d4_process_found = False
    for proc in psutil.process_iter(["name", "exe"]):
        if proc.name().lower() == "diablo iv.exe":
            d4_dir = Path(proc.exe()).parent
            tts_dll = d4_dir / "saapi64.dll"
            if not tts_dll.exists():
                LOGGER.warning(f"TTS DLL was not found in {d4_dir}. Have you followed the instructions in {SETUP_INSTRUCTIONS_URL} ?")
            else:
                LOGGER.debug(f"TTS DLL found at {tts_dll}")
            d4_process_found = True
            break
    if not d4_process_found:
        LOGGER.warning("No process named Diablo IV.exe was found and unable to automatically determine if TTS DLL is installed.")

    # Check if everything is set up properly in Diablo 4 settings
    local_prefs = get_d4_local_prefs_file()
    if local_prefs:
        with open(local_prefs) as file:
            prefs = file.read()
            if 'UseScreenReader "1"' not in prefs:
                LOGGER.error(
                    f"Use Screen Reader is not enabled in Accessibility Settings in D4. No items will be read. Read more about initial setup here: {SETUP_INSTRUCTIONS_URL}"
                )
            if 'UseThirdPartyReader "1"' not in prefs:
                LOGGER.error(
                    f"3rd Party Screen Reader is not enabled in Accessibility Settings in D4. No items will be read. Read more about initial setup here: {SETUP_INSTRUCTIONS_URL}"
                )
    else:
        LOGGER.warning("Unable to find a Diablo 4 local prefs file. Can't automatically check if TTS is configured properly in-game.")


def get_d4_local_prefs_file() -> Path | None:
    all_potential_files: list[Path] = [
        pathlib.Path.home() / "Documents" / "Diablo IV" / "LocalPrefs.txt",
        pathlib.Path.home() / "OneDrive" / "Documents" / "Diablo IV" / "LocalPrefs.txt",
        pathlib.Path.home() / "OneDrive" / "MyDocuments" / "Diablo IV" / "LocalPrefs.txt",
    ]

    existing_files: list[Path] = [file for file in all_potential_files if file.exists()]

    if len(existing_files) == 0:
        return None

    if len(existing_files) == 1:
        return existing_files[0]

    most_recently_modified_file = existing_files[0]
    for existing_file in existing_files[1:]:
        if existing_file.stat().st_mtime > most_recently_modified_file.stat().st_mtime:
            most_recently_modified_file = existing_file
    return most_recently_modified_file


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
