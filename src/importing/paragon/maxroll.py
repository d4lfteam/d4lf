from typing import Any

from src.importing.paragon.common import maxroll_board_slug, maxroll_glyph_slug
from src.paragon import NODES_LEN
from src.paragon import rotation_info_quarter_turn as _rotation_info_quarter_turn
from src.paragon import transform_flat_index as _transform_flat_index


def extract_maxroll_paragon_steps(
    active_profile: dict[str, Any], mapping_data: dict[str, Any]
) -> list[list[dict[str, Any]]]:
    """Extract paragon steps from Maxroll planner data."""
    steps_out: list[list[dict[str, Any]]] = []
    paragon = (active_profile or {}).get("paragon") or {}
    for step in paragon.get("steps") or []:
        boards_out: list[dict[str, Any]] = []
        for board in (step or {}).get("data") or []:
            board_id = (board or {}).get("id", "")
            glyph_id = (board or {}).get("glyph", "")
            rotation = int((board or {}).get("rotation", 0))
            nodes = [False] * NODES_LEN
            for loc_key in (board or {}).get("nodes") or {}:
                try:
                    loc = int(loc_key)
                except TypeError, ValueError:
                    continue
                idx = _transform_flat_index(loc=loc, rotation=rotation)
                if 0 <= idx < NODES_LEN:
                    nodes[idx] = True
            boards_out.append({
                "Name": maxroll_board_slug(board_id, mapping_data["paragonBoards"]),
                "Glyph": maxroll_glyph_slug(glyph_id, board_id, mapping_data["paragonGlyphs"]) if glyph_id else "",
                "Rotation": _rotation_info_quarter_turn(rotation),
                "Nodes": nodes,
                "BoardId": board_id,
                "GlyphId": glyph_id,
            })
        if boards_out:
            steps_out.append(boards_out)
    return steps_out
