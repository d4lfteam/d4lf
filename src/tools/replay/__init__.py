"""Public interfaces for screenshot replay capabilities."""

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
