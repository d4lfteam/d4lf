from typing import TYPE_CHECKING

from src.importing.conversion import as_string_keyed_mapping as _as_mapping
from src.importing.filters import PLAYER_CLASSES
from src.importing.paragon import as_int, as_list
from src.paragon import NODES_LEN
from src.paragon import rotation_info_degrees as _rotation_info_degrees
from src.paragon import transform_xy as _transform_xy

if TYPE_CHECKING:
    from collections.abc import Mapping

    from src.type_aliases import JsonObject, JsonValue


def _fix_starting_board_slug(board_slug: str) -> str:
    for player_class in PLAYER_CLASSES:
        board_slug = board_slug.replace(f"{player_class}-starter-board", f"{player_class}-starting-board")
    return board_slug


def extract_mobalytics_paragon_steps(paragon_data: Mapping[str, JsonValue]) -> list[list[JsonObject]]:
    """Extract paragon boards from Mobalytics preloaded-state build data."""
    boards_data = as_list((paragon_data or {}).get("boards"))
    nodes_data = as_list((paragon_data or {}).get("nodes"))
    boards_out: list[JsonObject] = []
    for board in boards_data:
        board_data = _as_mapping(board)
        raw_board_slug = _as_mapping(board_data.get("board")).get("slug", "")
        node_board_slug = raw_board_slug if isinstance(raw_board_slug, str) else ""
        board_slug = _fix_starting_board_slug(node_board_slug)
        glyph_slug = _as_mapping(board_data.get("glyph")).get("slug", "")
        glyph_slug = glyph_slug if isinstance(glyph_slug, str) else ""
        rotation = as_int(board_data.get("rotation"))
        nodes = [False] * NODES_LEN
        node_board_slugs = [node_board_slug]
        if board_slug != node_board_slug:
            node_board_slugs.append(board_slug)
        board_nodes = [
            node
            for node in nodes_data
            if isinstance((node_slug := _as_mapping(node).get("slug")), str)
            and any(node_slug.startswith(prefix + "-") for prefix in node_board_slugs)
        ]
        for node in board_nodes:
            slug = _as_mapping(node).get("slug", "")
            if not isinstance(slug, str):
                continue
            node_prefix = next((prefix for prefix in node_board_slugs if slug.startswith(prefix + "-")), None)
            if node_prefix is None:
                continue
            try:
                x_part, y_part = slug.removeprefix(node_prefix + "-").split("-", 1)
                x, y = int(x_part.lstrip("x")), int(y_part.lstrip("y"))
            except ValueError, IndexError:
                continue
            idx = _transform_xy(x=x, y=y, rotation_deg=rotation, base="mobalytics")
            if 0 <= idx < NODES_LEN:
                nodes[idx] = True
        boards_out.append({
            "Name": board_slug,
            "Glyph": glyph_slug,
            "Rotation": _rotation_info_degrees(rotation),
            "Nodes": nodes,
        })
    return [boards_out] if boards_out else []
