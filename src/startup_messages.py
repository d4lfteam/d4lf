import logging
from pathlib import Path

from src import __version__
from src.config.loader import IniConfigLoader

BANNER = (
    "════════════════════════════════════════════════════════════════════════════════\n"
    "D4LF - Diablo 4 Loot Filter\n"
    "════════════════════════════════════════════════════════════════════════════════"
)


def emit_startup_messages():
    """Emit the simplified startup banner for the new UI.

    No hotkey table. No extra formatting.
    """
    logger = logging.getLogger(__name__)
    logger.info(BANNER)


def emit_early_startup_logs():
    """Emit early startup logs exactly as before.

    - version
    - config path
    - missing profiles warning
    """
    logger = logging.getLogger(__name__)

    # 1. Running version
    logger.info(f"Running version v{__version__}")

    # 2. Adapt your configs
    logger.info(f"Adapt your configs via gui.bat or directly in: {IniConfigLoader().user_dir}")

    # 3. No profiles configured warning (if applicable)
    profiles_dir = Path(IniConfigLoader().user_dir) / "profiles"
    profile_files = list(profiles_dir.glob("*.ini"))

    if not profile_files:
        logger.warning(
            "No profiles have been configured so no filtering will be done. "
            "If this is a mistake, use the profiles section of the config tab "
            "of gui.bat to activate the profiles you want to use."
        )
