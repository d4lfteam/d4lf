"""Public interfaces for screenshot replay capabilities."""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.tools.replay.cropped_tooltip import ReplayConfig as CroppedTooltipConfig
    from src.tools.replay.cropped_tooltip import ReplayResult as CroppedTooltipResult
    from src.tools.replay.cropped_tooltip import run_replay as run_cropped_tooltip_replay
    from src.tools.replay.full_screenshot import ReplayConfig as FullScreenshotConfig
    from src.tools.replay.full_screenshot import ReplayResult as FullScreenshotResult
    from src.tools.replay.full_screenshot import run_replay as run_full_screenshot_replay
    from src.tools.replay.template_matching import ReplayConfig as TemplateMatchingConfig
    from src.tools.replay.template_matching import ReplayResult as TemplateMatchingResult
    from src.tools.replay.template_matching import run_replay as run_template_matching_replay

__all__ = [
    "CroppedTooltipConfig",
    "CroppedTooltipResult",
    "FullScreenshotConfig",
    "FullScreenshotResult",
    "TemplateMatchingConfig",
    "TemplateMatchingResult",
    "run_cropped_tooltip_replay",
    "run_full_screenshot_replay",
    "run_template_matching_replay",
]

_LAZY_EXPORTS = {
    "CroppedTooltipConfig": ("src.tools.replay.cropped_tooltip", "ReplayConfig"),
    "CroppedTooltipResult": ("src.tools.replay.cropped_tooltip", "ReplayResult"),
    "FullScreenshotConfig": ("src.tools.replay.full_screenshot", "ReplayConfig"),
    "FullScreenshotResult": ("src.tools.replay.full_screenshot", "ReplayResult"),
    "TemplateMatchingConfig": ("src.tools.replay.template_matching", "ReplayConfig"),
    "TemplateMatchingResult": ("src.tools.replay.template_matching", "ReplayResult"),
    "run_cropped_tooltip_replay": ("src.tools.replay.cropped_tooltip", "run_replay"),
    "run_full_screenshot_replay": ("src.tools.replay.full_screenshot", "run_replay"),
    "run_template_matching_replay": ("src.tools.replay.template_matching", "run_replay"),
}


def __getattr__(name: str) -> object:
    try:
        module_name, attribute_name = _LAZY_EXPORTS[name]
    except KeyError as error:
        message = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(message) from error
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
