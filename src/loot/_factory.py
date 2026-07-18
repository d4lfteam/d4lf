"""Selection of the configured vision-mode adapter."""

from typing import TYPE_CHECKING

from src.settings import VisionModeType

if TYPE_CHECKING:
    from ._contracts import VisionMode


def create_vision_mode(vision_mode_type: VisionModeType) -> VisionMode:
    if vision_mode_type == VisionModeType.fast:
        from ._fast import VisionModeFast  # ruff:ignore[import-outside-top-level]

        return VisionModeFast()

    from ._highlighting import VisionModeWithHighlighting  # ruff:ignore[import-outside-top-level]

    return VisionModeWithHighlighting()
