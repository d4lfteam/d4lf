import logging
from beautifultable import BeautifulTable
from src import __version__
from src.config.loader import IniConfigLoader
from src.item.filter import Filter

def emit_startup_messages():
    logger = logging.getLogger(__name__)

    logger.info(f"============ D4 Loot Filter {__version__} ============")

    table = BeautifulTable()
    table.set_style(BeautifulTable.STYLE_BOX_ROUNDED)
    table.rows.append([IniConfigLoader().advanced_options.run_vision_mode, "Run/Stop Vision Mode"])

    if not IniConfigLoader().advanced_options.vision_mode_only:
        table.rows.append([IniConfigLoader().advanced_options.run_filter, "Run/Stop Auto Filter"])
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

    for line in str(table).splitlines():
        logger.info(line)


def emit_early_startup_logs():
    logger = logging.getLogger(__name__)

    # 1. Running version
    logger.info(f"Running version v{__version__}")

    # 2. Adapt your configs
    logger.info(f"Adapt your configs via gui.bat or directly in: {IniConfigLoader().user_dir}")

    # 3. No profiles configured warning (if applicable)
    from pathlib import Path

    profiles_dir = Path(IniConfigLoader().user_dir) / "profiles"
    profile_files = list(profiles_dir.glob("*.ini"))

    if not profile_files:
        logger.warning(
            "No profiles have been configured so no filtering will be done. "
            "If this is a mistake, use the profiles section of the config tab "
            "of gui.bat to activate the profiles you want to use."
        )


