"""Application composition and desktop-runtime lifecycle."""

from importlib import import_module

from .assets import DISCORD_ICON, GITHUB_ICON, ICON_PATH, get_asset_path
from .startup import (
    SETUP_INSTRUCTIONS_URL,
    check_for_proper_tts_configuration,
    get_d4_local_prefs_file,
    prepare_runtime_directories,
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
]


def __getattr__(name: str) -> object:
    if name in {"BackendWorker", "get_perception_module", "run_backend"}:
        return getattr(import_module("src.app.backend"), name)
    message = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(message)
