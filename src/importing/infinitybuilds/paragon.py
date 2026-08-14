import dataclasses
from collections.abc import Mapping
from typing import TYPE_CHECKING

from src.importing.paragon import class_prefixed_slug
from src.importing.web import get_with_retry
from src.paragon import NODES_LEN
from src.paragon import class_slug_from_name as _class_slug_from_name
from src.paragon import rotation_info_quarter_turn as _rotation_info_quarter_turn
from src.paragon import transform_flat_index as _transform_flat_index

if TYPE_CHECKING:
    from src.type_aliases import JsonObject

INFINITYBUILDS_DATASETS_BASE_URL = "https://tools.infinitybuilds.gg/datasets/diablo4/en"


@dataclasses.dataclass
class InfinityBuildsParagonCatalog:
    """Board/glyph id to display label, resolved from InfinityBuilds datasets."""

    board_labels: dict[str, str]
    glyph_labels: dict[str, str]


def fetch_infinitybuilds_paragon_catalog() -> InfinityBuildsParagonCatalog:
    boards_response = get_with_retry(f"{INFINITYBUILDS_DATASETS_BASE_URL}/paragon-boards.json")
    glyphs_response = get_with_retry(f"{INFINITYBUILDS_DATASETS_BASE_URL}/glyphs.json")
    boards = boards_response.json().get("paragon", {}).get("boards", [])
    glyphs = glyphs_response.json().get("paragon", {}).get("glyphs", [])
    return InfinityBuildsParagonCatalog(
        board_labels={board["id"]: board.get("label", "") for board in boards if board.get("id")},
        glyph_labels={glyph["id"]: glyph.get("label", "") for glyph in glyphs if glyph.get("id")},
    )


def extract_infinitybuilds_paragon_steps(
    paragon_data: JsonObject, catalog: InfinityBuildsParagonCatalog, class_name: str
) -> list[list[JsonObject]]:
    """Extract paragon boards from an InfinityBuilds build variant."""
    class_slug = _class_slug_from_name(class_name)
    raw_active_nodes = paragon_data.get("activeNodes")
    active_nodes = (
        [node for node in raw_active_nodes if isinstance(node, str)] if isinstance(raw_active_nodes, list) else []
    )
    raw_slots = paragon_data.get("slots")
    slots = [slot for slot in raw_slots if isinstance(slot, Mapping)] if isinstance(raw_slots, list) else []
    raw_glyphs = paragon_data.get("glyphs")
    glyphs: dict[str, str] = (
        {str(node_id): str(glyph_id) for node_id, glyph_id in raw_glyphs.items()}
        if isinstance(raw_glyphs, Mapping)
        else {}
    )
    rotation_by_board: dict[str, int] = {}
    for slot in slots:
        board_id = slot.get("boardId")
        rotation = slot.get("rotation", 0)
        if isinstance(board_id, str) and isinstance(rotation, (int, float)) and not isinstance(rotation, bool):
            rotation_by_board[board_id] = int(rotation)
    nodes_by_board: dict[str, list[int]] = {}
    board_order: list[str] = []
    for node_id in active_nodes:
        board_id, _, index_str = node_id.rpartition("::")
        if not board_id or not index_str.isdigit():
            continue
        if board_id not in nodes_by_board:
            nodes_by_board[board_id] = []
            board_order.append(board_id)
        nodes_by_board[board_id].append(int(index_str))
    ordered_board_ids = [board for board in board_order if board not in rotation_by_board] + [
        slot["boardId"] for slot in slots if isinstance(slot.get("boardId"), str) and slot["boardId"] in nodes_by_board
    ]
    boards_out: list[JsonObject] = []
    for board_id in ordered_board_ids:
        rotation = rotation_by_board.get(board_id, 0)
        nodes = [False] * NODES_LEN
        for loc in nodes_by_board.get(board_id, []):
            idx = _transform_flat_index(loc=loc, rotation=rotation)
            if 0 <= idx < NODES_LEN:
                nodes[idx] = True
        glyph_id = next((gid for node_id, gid in glyphs.items() if node_id.startswith(f"{board_id}::")), None)
        boards_out.append({
            "Name": class_prefixed_slug(str(catalog.board_labels.get(board_id) or board_id), class_slug),
            "Glyph": class_prefixed_slug(catalog.glyph_labels.get(glyph_id) or glyph_id, class_slug)
            if glyph_id
            else "",
            "Rotation": _rotation_info_quarter_turn(rotation),
            "Nodes": nodes,
            "BoardId": board_id,
            "GlyphId": glyph_id,
        })
    return [boards_out] if boards_out else []
