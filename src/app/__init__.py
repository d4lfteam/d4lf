"""Application composition and desktop-runtime lifecycle."""

from src.app.assets import DISCORD_ICON, GITHUB_ICON, ICON_PATH, get_asset_path
from src.app.backend import run_backend
from src.app.startup import (
    SETUP_INSTRUCTIONS_URL,
    check_for_proper_tts_configuration,
    get_d4_local_prefs_file,
    prepare_runtime_directories,
    show_settings_load_error,
)

__all__ = [
    "DISCORD_ICON",
    "GITHUB_ICON",
    "ICON_PATH",
    "SETUP_INSTRUCTIONS_URL",
    "check_for_proper_tts_configuration",
    "get_asset_path",
    "get_d4_local_prefs_file",
    "prepare_runtime_directories",
    "run_backend",
    "show_settings_load_error",
]
