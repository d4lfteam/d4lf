import datetime
import re
from typing import Any

from src import __version__
from src.importing._conversion import as_string_keyed_mapping as _as_mapping
from src.paragon import prefix_with_class_slug as _prefix_with_class_slug
from src.paragon import slugify as _slugify
from src.profiles import ParagonPayloadModel


def as_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def as_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def maxroll_class_slug(board_id: str) -> str:
    match = re.match(r"^Paragon_([A-Za-z]+)_\d+$", board_id or "")
    return _slugify(match.group(1)) if match else ""


def maxroll_board_slug(board_id: str, board_data: dict[str, object]) -> str:
    cls = maxroll_class_slug(board_id)
    name = _as_mapping(board_data.get(board_id)).get("name")
    name_slug = _slugify(name) if isinstance(name, str) else ""
    return f"{cls}-{name_slug}" if cls and name_slug else _slugify(board_id)


def maxroll_glyph_slug(glyph_id: str, board_id: str, glyph_data: dict[str, object]) -> str:
    cls = maxroll_class_slug(board_id)
    name = _as_mapping(glyph_data.get(glyph_id)).get("name", glyph_id)
    name_slug = _slugify(name) if isinstance(name, str) else _slugify(glyph_id)
    return f"{cls}-{name_slug}" if cls and name_slug else _slugify(glyph_id)


def build_paragon_profile_payload(
    build_name: str, source_url: str, paragon_boards_list: list[list[dict[str, Any]]]
) -> ParagonPayloadModel:
    """Build the Paragon payload intended to be embedded into a profile YAML."""
    return ParagonPayloadModel(
        Name=build_name,
        Source=source_url,
        GeneratedAt=datetime.datetime.now(tz=datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        Generator=f"d4lf v{__version__}",
        ParagonBoardsList=paragon_boards_list,
    )


def class_prefixed_slug(raw_value: str, class_slug: str) -> str:
    return _prefix_with_class_slug(_slugify(raw_value), class_slug)
