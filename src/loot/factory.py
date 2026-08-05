"""Selection of the configured vision-mode adapter."""

from typing import TYPE_CHECKING

from src.loot import fast, highlighting
from src.settings import VisionModeType

if TYPE_CHECKING:
    from src.loot.contracts import VisionMode


def create_vision_mode(vision_mode_type: VisionModeType) -> VisionMode:
    if vision_mode_type == VisionModeType.fast:
        return fast.VisionModeFast()

    return highlighting.VisionModeWithHighlighting()
