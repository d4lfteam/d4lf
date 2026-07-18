"""Public loot filtering and vision-mode capability facade."""

from ._colors import FilterColors, get_filter_colors
from ._contracts import VisionMode
from ._factory import create_vision_mode
from ._orchestration import run_loot_filter


def create_script_handler():
    """Create the configured game-script coordinator for application startup."""
    from src.scripts.handler import ScriptHandler  # ruff:ignore[import-outside-top-level]

    return ScriptHandler()


__all__ = [
    "FilterColors",
    "VisionMode",
    "create_script_handler",
    "create_vision_mode",
    "get_filter_colors",
    "run_loot_filter",
]
