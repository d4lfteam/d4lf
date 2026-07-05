from __future__ import annotations

import re

GRID = 21
NODES_LEN = GRID * GRID


def slugify(s: str) -> str:
    """Collapse planner labels into stable lowercase slug tokens."""
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def class_slug_from_name(class_name: str) -> str:
    """Normalize a build class label into the shared export slug format."""
    class_name = (class_name or "").strip().lower()
    if not class_name or class_name == "unknown":
        return ""
    # Normalize planner-provided labels so all exporters use the same class prefix.
    return re.sub(r"[^a-z0-9\-]", "", re.sub(r"[\s_]+", "-", class_name))


def prefix_with_class_slug(slug: str, class_slug: str) -> str:
    """Prefix a slug with its class name once, matching the other exporters."""
    if not slug:
        return slug
    if not class_slug:
        return slug
    if slug.startswith(class_slug + "-"):
        return slug
    return f"{class_slug}-{slug}"


def rotation_info_quarter_turn(rot: int) -> str:
    """Format a 0-3 quarter-turn rotation (Maxroll's and InfinityBuilds' native format)."""
    return {0: "0°", 1: "90°", 2: "180°", 3: "270°"}.get(rot, "?°")


def rotation_info_degrees(rot: int) -> str:
    rot = rot % 360
    return {0: "0°", 90: "90°", 180: "180°", 270: "270°"}.get(rot, "?°")


def parse_rotation(rot_str: str) -> int:
    """Extract and sanitize the supported board rotation angle."""
    m = re.search(r"(\d+)", rot_str or "")
    deg = int(m.group(1)) % 360 if m else 0
    return deg if deg in (0, 90, 180, 270) else 0


def transform_flat_index(loc: int, rotation: int) -> int:
    """Transform a 0-based, row-major flat node index into the rotated Nodes[] index.

    This follows the exact switch used in Diablo4Companion BuildsManagerMaxroll. Both Maxroll and
    InfinityBuilds represent node positions and board rotation this same way (a flat 0-440 index
    into the unrotated 21x21 grid, plus a 0-3 quarter-turn rotation), so this transform is shared.
    """
    x = loc % GRID
    y = loc // GRID
    xt = x
    yt = y

    match rotation:
        case 0:
            return loc
        case 1:
            xt = GRID - y
            yt = x
            xt -= 1
            return yt * GRID + xt
        case 2:
            xt = GRID - x
            yt = GRID - y
            xt -= 1
            yt -= 1
            return yt * GRID + xt
        case 3:
            xt = y
            yt = GRID - x
            yt -= 1
            return yt * GRID + xt
        case _:
            return loc


def transform_xy(x: int, y: int, rotation_deg: int, base: str) -> int:
    """Shared x/y to Nodes[] transform.

    base:
      - 'd4builds' uses 1-based r/c coordinates.
      - 'mobalytics' uses 1-based x/y coordinates.

    The formulas mirror Diablo4Companion's implementations for each source.
    """
    rotation_deg = rotation_deg % 360

    xt = x
    yt = y

    if base in {"d4builds", "mobalytics"}:
        # both sources provide 1-based coords in the '0°' case and need (x-1, y-1)
        if rotation_deg in {0, 360}:
            xt -= 1
            yt -= 1
        elif rotation_deg == 90:
            xt = GRID - y
            yt = x
            yt -= 1
        elif rotation_deg == 180:
            xt = GRID - x
            yt = GRID - y
        elif rotation_deg == 270:
            xt = y
            yt = GRID - x
            xt -= 1

    return yt * GRID + xt


def nodes_to_grid(nodes: list[int] | list[bool]) -> list[list[bool]]:
    """Convert the flat node list into a 2D boolean grid."""
    return [[bool(nodes[y * GRID + x]) for x in range(GRID)] for y in range(GRID)]
