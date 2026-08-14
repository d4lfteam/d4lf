"""d2core final Paragon snapshot transformation."""

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, cast

from src.importing.d2core.errors import OPTIONAL_ENTRY_JOIN
from src.importing.paragon import class_prefixed_slug
from src.paragon import NODES_LEN, rotation_info_quarter_turn

if TYPE_CHECKING:
    from src.importing.d2core.catalog import CatalogStore
    from src.type_aliases import JsonObject, JsonValue

Warn = Callable[[str, str, str, str], None]


def normalize_paragon(
    raw_variant: Mapping[str, JsonValue], *, class_name: str, variant_name: str, catalogs: CatalogStore, warn: Warn
) -> list[list[JsonObject]]:
    raw_boards = raw_variant.get("paragon")
    if not isinstance(raw_boards, Mapping):
        return []
    paragon = catalogs.data.get("paragon", {})
    class_catalog = _class_catalog(paragon, class_name)
    boards = class_catalog.get("board", {}) if isinstance(class_catalog, Mapping) else {}
    glyphs = class_catalog.get("glyph", {}) if isinstance(class_catalog, Mapping) else {}
    result: list[JsonObject] = []
    for board_key, raw_board in sorted(raw_boards.items(), key=_board_index):
        if not isinstance(raw_board, Mapping) or raw_board.get("deleted") is True:
            continue
        board = boards.get(str(board_key)) if isinstance(boards, Mapping) else None
        if not isinstance(board, Mapping):
            warn(OPTIONAL_ENTRY_JOIN, variant_name, "paragon", str(board_key))
            continue
        nodes = [False] * NODES_LEN
        board_data = board.get("data", [])
        raw_node_entries = raw_board.get("data")
        node_entries = cast("list[JsonValue]", raw_node_entries) if isinstance(raw_node_entries, list) else []
        for entry in node_entries:
            row, column, node_key = _node_entry(entry)
            if (
                row is None
                or column is None
                or node_key is None
                or not _catalog_node(board_data, row, column, node_key)
            ):
                warn(OPTIONAL_ENTRY_JOIN, variant_name, "paragon", str(node_key or entry))
                continue
            transformed = _rotate_index(row, column, _int(raw_board.get("rotate")))
            if 0 <= transformed < NODES_LEN:
                nodes[transformed] = True
        glyph_id, glyph_name = _glyph(cast("Mapping[str, JsonValue]", raw_board), glyphs, _class_slug(class_name))
        result.append({
            "Name": class_prefixed_slug(str(board.get("name", board_key)), _class_slug(class_name)),
            "Glyph": glyph_name,
            "Rotation": rotation_info_quarter_turn(_int(raw_board.get("rotate"))),
            "Nodes": nodes,
            "BoardId": str(board_key),
            "GlyphId": glyph_id,
        })
    return [result] if result else []


def _class_catalog(paragon: Mapping[str, JsonValue], class_name: str) -> Mapping[str, JsonValue]:
    for key in (class_name, class_name.title(), class_name.casefold(), class_name.upper()):
        value = paragon.get(key)
        if isinstance(value, Mapping):
            return cast("Mapping[str, JsonValue]", value)
    empty_catalog: dict[str, JsonValue] = {}
    return empty_catalog


def _glyph(raw_board: Mapping[str, JsonValue], glyphs: JsonValue, class_slug: str) -> tuple[str, str]:
    raw = raw_board.get("glyph")
    if not isinstance(raw, Mapping) or not raw or not isinstance(glyphs, Mapping):
        return "", ""
    _glyph_id, source_key = next(iter(raw.items()))
    glyph = glyphs.get(str(source_key))
    if not isinstance(glyph, Mapping):
        return str(source_key), ""
    return str(source_key), class_prefixed_slug(str(glyph.get("name", source_key)), class_slug)


def _catalog_node(data: JsonValue, row: int, column: int, node_key: str) -> bool:
    if not isinstance(data, list) or not 0 <= row < len(data):
        return False
    cells = str(data[row]).split(",")
    return 0 <= column < len(cells) and cells[column] == node_key


def _node_entry(entry: JsonValue) -> tuple[int | None, int | None, str | None]:
    if not isinstance(entry, str):
        return None, None, None
    parts = entry.split("_", 2)
    if len(parts) != 3:
        return None, None, None
    try:
        return int(parts[0]), int(parts[1]), parts[2]
    except ValueError:
        return None, None, None


def _rotate_index(row: int, column: int, rotation: int) -> int:
    for _ in range(rotation % 4):
        row, column = column, 20 - row
    return row * 21 + column


def _board_index(item: tuple[str, JsonValue]) -> int:
    value = item[1].get("index", 0) if isinstance(item[1], Mapping) else 0
    try:
        return int(cast("str | int", value))
    except TypeError, ValueError:
        return 0


def _int(value: JsonValue) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _class_slug(class_name: str) -> str:
    return class_name.casefold().replace(" ", "-") if class_name.casefold() != "unknown" else ""
