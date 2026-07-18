"""Public Paragon capability facade."""

# Overlay functions are loaded lazily to keep profile/model imports headless.

from ._transform import (
    GRID,
    NODES_LEN,
    class_slug_from_name,
    nodes_to_grid,
    parse_rotation,
    prefix_with_class_slug,
    rotation_info_degrees,
    rotation_info_quarter_turn,
    slugify,
    transform_flat_index,
    transform_xy,
)

__all__ = [
    "GRID",
    "NODES_LEN",
    "class_slug_from_name",
    "format_board_display_text",
    "load_builds_from_path",
    "nodes_to_grid",
    "parse_rotation",
    "prefix_with_class_slug",
    "request_close",
    "rotation_info_degrees",
    "rotation_info_quarter_turn",
    "run_paragon_overlay",
    "slugify",
    "transform_flat_index",
    "transform_xy",
]


def __getattr__(name: str):
    if name in {"format_board_display_text", "load_builds_from_path", "request_close", "run_paragon_overlay"}:
        from . import _overlay

        return getattr(_overlay, name)
    message = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(message)
