from typing import TYPE_CHECKING

from src.importing.conversion import as_string_keyed_mapping as _as_mapping
from src.importing.conversion import as_string_keyed_mapping_list as _as_mapping_list
from src.importing.conversion import as_text as _as_text
from src.importing.paragon import maxroll_board_slug, maxroll_glyph_slug
from src.paragon import NODES_LEN
from src.paragon import rotation_info_quarter_turn as _rotation_info_quarter_turn
from src.paragon import transform_flat_index as _transform_flat_index

if TYPE_CHECKING:
    from src.type_aliases import JsonObject


def extract_maxroll_paragon_steps(active_profile: JsonObject, mapping_data: JsonObject) -> list[list[JsonObject]]:
    """Extract paragon steps from Maxroll planner data."""
    steps_out: list[list[JsonObject]] = []
    paragon = _as_mapping(active_profile.get("paragon"))
    for step in _as_mapping_list(paragon.get("steps")):
        boards_out: list[JsonObject] = []
        for board in _as_mapping_list(step.get("data")):
            board_id = _as_text(board.get("id"))
            glyph_id = _as_text(board.get("glyph"))
            raw_rotation = board.get("rotation", 0)
            rotation = int(raw_rotation) if isinstance(raw_rotation, (int, float)) else 0
            nodes = [False] * NODES_LEN
            for loc_key in _as_mapping(board.get("nodes")):
                try:
                    loc = int(loc_key)
                except TypeError, ValueError:
                    continue
                idx = _transform_flat_index(loc=loc, rotation=rotation)
                if 0 <= idx < NODES_LEN:
                    nodes[idx] = True
            boards_out.append({
                "Name": maxroll_board_slug(board_id, _as_mapping(mapping_data.get("paragonBoards"))),
                "Glyph": maxroll_glyph_slug(glyph_id, board_id, _as_mapping(mapping_data.get("paragonGlyphs")))
                if glyph_id
                else "",
                "Rotation": _rotation_info_quarter_turn(rotation),
                "Nodes": nodes,
                "BoardId": board_id,
                "GlyphId": glyph_id,
            })
        if boards_out:
            steps_out.append(boards_out)
    return steps_out
