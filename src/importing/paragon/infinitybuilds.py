import dataclasses
from typing import Any

from src.importing._web import get_with_retry
from src.importing.paragon.common import class_prefixed_slug
from src.paragon import NODES_LEN
from src.paragon import class_slug_from_name as _class_slug_from_name
from src.paragon import rotation_info_quarter_turn as _rotation_info_quarter_turn
from src.paragon import transform_flat_index as _transform_flat_index

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
    paragon_data: dict[str, Any], catalog: InfinityBuildsParagonCatalog, class_name: str
) -> list[list[dict[str, Any]]]:
    """Extract paragon boards from an InfinityBuilds build variant."""
    class_slug = _class_slug_from_name(class_name)
    active_nodes = paragon_data.get("activeNodes") or []
    slots = paragon_data.get("slots") or []
    glyphs = paragon_data.get("glyphs") or {}
    rotation_by_board = {slot["boardId"]: int(slot.get("rotation", 0)) for slot in slots if slot.get("boardId")}
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
        slot["boardId"] for slot in slots if slot.get("boardId") in nodes_by_board
    ]
    boards_out: list[dict[str, Any]] = []
    for board_id in ordered_board_ids:
        rotation = rotation_by_board.get(board_id, 0)
        nodes = [False] * NODES_LEN
        for loc in nodes_by_board.get(board_id, []):
            idx = _transform_flat_index(loc=loc, rotation=rotation)
            if 0 <= idx < NODES_LEN:
                nodes[idx] = True
        glyph_id = next((gid for node_id, gid in glyphs.items() if node_id.startswith(board_id + "::")), None)
        boards_out.append({
            "Name": class_prefixed_slug(catalog.board_labels.get(board_id) or board_id, class_slug),
            "Glyph": class_prefixed_slug(catalog.glyph_labels.get(glyph_id) or glyph_id, class_slug)
            if glyph_id
            else "",
            "Rotation": _rotation_info_quarter_turn(rotation),
            "Nodes": nodes,
            "BoardId": board_id,
            "GlyphId": glyph_id,
        })
    return [boards_out] if boards_out else []
