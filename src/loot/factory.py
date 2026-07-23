"""Selection of the configured vision-mode adapter."""

from typing import TYPE_CHECKING

from src.settings import VisionModeType

if TYPE_CHECKING:
    from src.loot.contracts import VisionMode


def create_vision_mode(vision_mode_type: VisionModeType) -> VisionMode:
    if vision_mode_type == VisionModeType.fast:
        from src.loot.fast import VisionModeFast  # ruff:ignore[import-outside-top-level]

        return VisionModeFast()

    from src.loot.highlighting import VisionModeWithHighlighting  # ruff:ignore[import-outside-top-level]

    return VisionModeWithHighlighting()
