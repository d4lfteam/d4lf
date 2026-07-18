import dataclasses
import datetime
import logging
import re
import time
from typing import TYPE_CHECKING, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from src import __version__
from src.importing._conversion import as_string_keyed_mapping as _as_mapping
from src.importing._filters import PLAYER_CLASSES
from src.importing._web import get_with_retry
from src.paragon import NODES_LEN
from src.paragon import class_slug_from_name as _class_slug_from_name
from src.paragon import prefix_with_class_slug as _prefix_with_class_slug
from src.paragon import rotation_info_degrees as _rotation_info_degrees
from src.paragon import rotation_info_quarter_turn as _rotation_info_quarter_turn
from src.paragon import slugify as _slugify
from src.paragon import transform_flat_index as _transform_flat_index
from src.paragon import transform_xy as _transform_xy
from src.profiles import ParagonPayloadModel

if TYPE_CHECKING:
    from collections.abc import Mapping

    from selenium.webdriver.remote.webdriver import WebDriver


LOGGER = logging.getLogger(__name__)


def _as_list(value: object) -> list[object]:
    result: list[object] = []
    if isinstance(value, list):
        result.extend(value)
    return result


def _as_int(value: object, default: int = 0) -> int:
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


def _maxroll_class_slug(board_id: str) -> str:
    # Example: "Paragon_Paladin_02" -> "paladin"
    m = re.match(r"^Paragon_([A-Za-z]+)_\d+$", board_id or "")
    return _slugify(m.group(1)) if m else ""


def _maxroll_board_slug(board_id: str, board_data: Mapping[str, object]) -> str:
    cls = _maxroll_class_slug(board_id)
    name = _as_mapping(board_data.get(board_id)).get("name")
    name_slug = _slugify(name) if isinstance(name, str) else ""
    return f"{cls}-{name_slug}" if cls and name_slug else _slugify(board_id)


def _maxroll_glyph_slug(glyph_id: str, board_id: str, glyph_data: Mapping[str, object]) -> str:
    # We prefix with class for consistency with Mobalytics output.
    cls = _maxroll_class_slug(board_id)
    name = _as_mapping(glyph_data.get(glyph_id)).get("name", glyph_id)
    name_slug = _slugify(name) if isinstance(name, str) else _slugify(glyph_id)
    return f"{cls}-{name_slug}" if cls and name_slug else _slugify(glyph_id)


#
# =============================================================================
# PAYLOAD BUILDER
# =============================================================================


def build_paragon_profile_payload(
    build_name: str, source_url: str, paragon_boards_list: list[list[dict[str, Any]]]
) -> ParagonPayloadModel:
    """Build the Paragon payload intended to be embedded into a profile YAML.

    The structure matches the existing JSON export payload (without the outer list wrapper).
    """
    return ParagonPayloadModel(
        Name=build_name,
        Source=source_url,
        GeneratedAt=datetime.datetime.now(tz=datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        Generator=f"d4lf v{__version__}",
        ParagonBoardsList=paragon_boards_list,
    )


#
# =============================================================================
# MAXROLL EXPORT
# =============================================================================


def extract_maxroll_paragon_steps(
    active_profile: dict[str, Any], mapping_data: dict[str, Any]
) -> list[list[dict[str, Any]]]:
    """Extract paragon steps from Maxroll planner data.

    Matches the rotation + node-index transformation used in Diablo4Companion.
    """
    steps_out: list[list[dict[str, Any]]] = []
    paragon = (active_profile or {}).get("paragon") or {}
    steps = paragon.get("steps") or []

    for step in steps:
        boards_out: list[dict[str, Any]] = []
        for bd in (step or {}).get("data") or []:
            board_id = (bd or {}).get("id", "")
            glyph_id = (bd or {}).get("glyph", "")
            rotation = int((bd or {}).get("rotation", 0))
            nodes_bool = [False] * NODES_LEN

            # Maxroll stores active nodes as a dict keyed by flat node indices.
            nodes_dict = (bd or {}).get("nodes") or {}
            for loc_key in nodes_dict:
                try:
                    loc = int(loc_key)
                except TypeError, ValueError:
                    loc = None
                if loc is None:
                    continue
                idx = _transform_flat_index(loc=loc, rotation=rotation)
                if 0 <= idx < NODES_LEN:
                    nodes_bool[idx] = True

            boards_out.append({
                "Name": _maxroll_board_slug(board_id, mapping_data["paragonBoards"]),
                "Glyph": _maxroll_glyph_slug(glyph_id, board_id, mapping_data["paragonGlyphs"]) if glyph_id else "",
                "Rotation": _rotation_info_quarter_turn(rotation),
                "Nodes": nodes_bool,
                "BoardId": board_id,
                "GlyphId": glyph_id,
            })

        if boards_out:
            steps_out.append(boards_out)

    return steps_out


#
# =============================================================================
# MOBALYTICS EXPORT
# =============================================================================


def _fix_mobalytics_starting_board_slug(board_slug: str) -> str:
    """Normalize Mobalytics' starter-board naming to the shared starting-board form."""
    for player_class in PLAYER_CLASSES:
        board_slug = board_slug.replace(f"{player_class}-starter-board", f"{player_class}-starting-board")
    return board_slug


def extract_mobalytics_paragon_steps(paragon_data: Mapping[str, object]) -> list[list[dict[str, Any]]]:
    """Extract paragon boards from Mobalytics preloaded-state build variant.

    Matches the rotation + node-index transformation used in Diablo4Companion.
    """
    paragon = paragon_data or {}
    boards_data = _as_list(paragon.get("boards"))
    nodes_data = _as_list(paragon.get("nodes"))

    boards_out: list[dict[str, Any]] = []

    for board in boards_data:
        board_data = _as_mapping(board)
        board_slug = _as_mapping(board_data.get("board")).get("slug", "")
        board_slug = board_slug if isinstance(board_slug, str) else ""
        board_slug = _fix_mobalytics_starting_board_slug(board_slug)

        glyph_slug = _as_mapping(board_data.get("glyph")).get("slug", "")
        glyph_slug = glyph_slug if isinstance(glyph_slug, str) else ""
        rotation = _as_int(board_data.get("rotation"))

        nodes_bool = [False] * NODES_LEN
        # Mobalytics exposes nodes as one flat list, so filter it back down to the current board first.
        board_nodes = [
            n
            for n in nodes_data
            if isinstance((node_slug := _as_mapping(n).get("slug")), str) and node_slug.startswith(board_slug)
        ]

        for n in board_nodes:
            slug = _as_mapping(n).get("slug", "")
            if not isinstance(slug, str):
                continue
            node_position = slug.replace(board_slug + "-", "")
            try:
                x_part, y_part = node_position.split("-", 1)
                x = int(x_part.lstrip("x"))
                y = int(y_part.lstrip("y"))
            except ValueError, IndexError:
                x = None
                y = None
            if x is None or y is None:
                continue

            idx = _transform_xy(x=x, y=y, rotation_deg=rotation, base="mobalytics")
            if 0 <= idx < NODES_LEN:
                nodes_bool[idx] = True

        boards_out.append({
            "Name": board_slug,
            "Glyph": glyph_slug,
            "Rotation": _rotation_info_degrees(rotation),
            "Nodes": nodes_bool,
        })

    return [boards_out] if boards_out else []


#
# =============================================================================
# D4BUILDS EXPORT
# =============================================================================


def _parse_d4builds_paragon_boards(driver: WebDriver, class_slug: str) -> list[list[dict[str, Any]]]:
    """Parse D4Builds paragon boards from the currently loaded page.

    D4Builds does not expose the board export as a ready-made JSON payload, so this
    parser reconstructs one from DOM text, element attributes, and active tile classes.
    """
    boards_out: list[dict[str, Any]] = []
    try:
        board_elements = driver.find_elements(By.CLASS_NAME, "paragon__board")
    except Exception:
        LOGGER.debug("Failed to read D4Builds paragon board elements.", exc_info=True)
        board_elements = []

    for board_elem in board_elements:
        name_raw = ""
        lines = []
        name_display = ""
        try:
            name_raw = board_elem.find_element(By.CLASS_NAME, "paragon__board__name").get_attribute("innerText") or ""
            lines = [ln.strip() for ln in (name_raw or "").splitlines() if ln.strip()]
            # Prefer first line that contains letters (D4Builds sometimes shows just a numeric index on line 1)
            name_display = next((ln for ln in lines if any(ch.isalpha() for ch in ln)), (lines[0] if lines else ""))
        except Exception:
            LOGGER.debug("Failed to read D4Builds board name.", exc_info=True)
            name_display = ""

        # Try to detect a stable board id/slug from element attributes (best effort)
        board_id = ""
        try:
            attrs = driver.execute_script(
                "var a=arguments[0].attributes; var o={}; for (var i=0;i<a.length;i++){o[a[i].name]=a[i].value}; return o;",
                board_elem,
            )
            if isinstance(attrs, dict):
                for key in ("data-board", "data-board-id", "data-id", "data-name", "data-board-name", "data-boardname"):
                    v = attrs.get(key)
                    if isinstance(v, str) and v.strip():
                        board_id = v.strip()
                        break
                if not board_id:
                    for v in attrs.values():
                        if isinstance(v, str):
                            vv = v.strip()
                            if vv and "-" in vv and re.fullmatch(r"[A-Za-z0-9_-]{3,64}", vv):
                                board_id = vv
                                break
        except Exception:
            LOGGER.debug("Failed to infer board id (continuing).", exc_info=True)

        name_slug = _slugify(board_id or name_display)
        name_slug = _prefix_with_class_slug(name_slug, class_slug)
        if not name_slug and lines and str(lines[0]).isdigit():
            name_slug = f"board-{lines[0]}"

        glyph_raw = ""
        try:
            glyph_elems = board_elem.find_elements(By.CLASS_NAME, "paragon__board__name__glyph")
            if glyph_elems:
                glyph_raw = (glyph_elems[0].get_attribute("innerText") or "").strip()
        except Exception:
            LOGGER.debug("Failed to read glyph name (continuing).", exc_info=True)

        glyph_display = (glyph_raw or "").replace("(", "").replace(")", "").strip()
        glyph_slug = _slugify(glyph_display)
        glyph_slug = _prefix_with_class_slug(glyph_slug, class_slug)

        style_str = board_elem.get_attribute("style") or ""
        rotate_int = 0
        if "rotate(" in style_str:
            mm = re.search(r"rotate\(([-\d]+)deg\)", style_str)
            if mm:
                try:
                    rotate_int = int(mm.group(1)) % 360
                except ValueError:
                    rotate_int = 0

        nodes = [False] * NODES_LEN

        try:
            tile_elems = board_elem.find_elements(By.CLASS_NAME, "paragon__board__tile")
        except Exception:
            LOGGER.debug("Failed to read D4Builds board tiles.", exc_info=True)
            tile_elems = []

        # D4Builds encodes the active grid coordinates in CSS class tokens like "r2 c10".
        for tile in tile_elems:
            cls = tile.get_attribute("class") or ""
            if "active" not in cls:
                continue
            parts = [pp for pp in cls.split() if pp]
            # Example: "paragon__board__tile r2 c10 active enabled"
            r_part = next((x for x in parts if x.startswith("r")), "r0")
            c_part = next((x for x in parts if x.startswith("c")), "c0")
            r = int("".join(ch for ch in r_part if ch.isdigit()) or "0")
            c = int("".join(ch for ch in c_part if ch.isdigit()) or "0")

            idx = _transform_xy(x=c, y=r, rotation_deg=rotate_int, base="d4builds")
            if 0 <= idx < NODES_LEN:
                nodes[idx] = True

        boards_out.append({
            "Name": name_slug or "paragon-board",
            "Glyph": glyph_slug,
            "Rotation": _rotation_info_degrees(rotate_int),
            "Nodes": nodes,
        })

    return [boards_out]


def extract_d4builds_paragon_steps(
    driver: WebDriver, class_name: str = "", *, wait: WebDriverWait[WebDriver] | None = None
) -> list[list[dict[str, Any]]]:
    """Extract paragon boards from D4Builds using Selenium.

    This reuses the existing Selenium session/page state created by the importer. We only
    click/wait for the Paragon tab if boards are not already present in the DOM.
    """
    class_slug = _class_slug_from_name(class_name)

    if wait is None:
        wait = WebDriverWait(driver, 10)

    # Fast path: if boards are already present, don't click/wait again.
    try:
        if driver.find_elements(By.CLASS_NAME, "paragon__board"):
            return _parse_d4builds_paragon_boards(driver, class_slug)
    except Exception:
        LOGGER.debug("Could not query for existing D4Builds paragon boards (continuing).", exc_info=True)

    # Best effort: ensure the navigation is present before attempting to click Paragon.
    try:
        wait.until(lambda d: len(d.find_elements(By.CLASS_NAME, "builder__navigation__link")) > 0)
    except Exception:
        LOGGER.debug("Timed out waiting for D4Builds navigation links (continuing).", exc_info=True)

    # Switch to Paragon tab (D4Builds uses left navigation links)
    try:
        nav_links = driver.find_elements(By.CLASS_NAME, "builder__navigation__link")
        if len(nav_links) >= 3:
            driver.execute_script("arguments[0].click();", nav_links[2])
        else:
            # Fallback: click any element containing 'Paragon'
            el = driver.find_element(By.XPATH, "//*[contains(normalize-space(.), 'Paragon')]")
            driver.execute_script("arguments[0].click();", el)
        time.sleep(0.25)
    except Exception:
        # Not fatal: sometimes paragon is already visible or site changed
        LOGGER.debug("Could not click Paragon tab (continuing).", exc_info=True)

    # Wait for paragon boards to appear (best effort)
    try:
        wait.until(lambda d: len(d.find_elements(By.CLASS_NAME, "paragon__board")) > 0)
    except Exception:
        LOGGER.debug("Timed out waiting for D4Builds paragon boards (continuing).", exc_info=True)

    return _parse_d4builds_paragon_boards(driver, class_slug)


#
# =============================================================================
# INFINITYBUILDS EXPORT
# =============================================================================

INFINITYBUILDS_DATASETS_BASE_URL = "https://tools.infinitybuilds.gg/datasets/diablo4/en"


@dataclasses.dataclass
class InfinityBuildsParagonCatalog:
    """Board/glyph id -> display label, resolved from InfinityBuilds' public datasets."""

    board_labels: dict[str, str]
    glyph_labels: dict[str, str]


def fetch_infinitybuilds_paragon_catalog() -> InfinityBuildsParagonCatalog:
    """Fetch the board and glyph label catalogs used to make InfinityBuilds' ids readable.

    These are served pre-compressed as brotli under a `.br` extension (as seen in the site's own
    network calls), but the same data is also available at a `.json` path with plain gzip, which
    httpx already handles without needing an extra brotli dependency.
    """
    boards_response = get_with_retry(f"{INFINITYBUILDS_DATASETS_BASE_URL}/paragon-boards.json")
    glyphs_response = get_with_retry(f"{INFINITYBUILDS_DATASETS_BASE_URL}/glyphs.json")
    boards = boards_response.json().get("paragon", {}).get("boards", [])
    glyphs = glyphs_response.json().get("paragon", {}).get("glyphs", [])
    return InfinityBuildsParagonCatalog(
        board_labels={b["id"]: b.get("label", "") for b in boards if b.get("id")},
        glyph_labels={g["id"]: g.get("label", "") for g in glyphs if g.get("id")},
    )


def _infinitybuilds_named_slug(raw_id: str, label: str | None, class_slug: str) -> str:
    """Slugify a catalog label, falling back to slugifying the raw id if it's unknown."""
    name_slug = _slugify(label) if label else _slugify(raw_id)
    return _prefix_with_class_slug(name_slug, class_slug)


def extract_infinitybuilds_paragon_steps(
    paragon_data: dict[str, Any], catalog: InfinityBuildsParagonCatalog, class_name: str
) -> list[list[dict[str, Any]]]:
    """Extract paragon boards from an InfinityBuilds build variant's embedded paragon data.

    InfinityBuilds ships this directly as a `paragon` key alongside `gear`/`skills` in the same
    React Flight payload the importer already parses, so no extra requests are needed to know
    which nodes/glyphs/boards a build uses (only to resolve their display names, via `catalog`).
    Node ids look like "paragon-board::<board-id>::<flat-index>", where <flat-index> is already
    the same 0-based, row-major grid index (and slot rotation is already 0-3 quarter turns) that
    Maxroll uses, so the shared transform applies unchanged.
    """
    class_slug = _class_slug_from_name(class_name)
    active_nodes = paragon_data.get("activeNodes") or []
    slots = paragon_data.get("slots") or []
    glyphs = paragon_data.get("glyphs") or {}

    rotation_by_board = {s["boardId"]: int(s.get("rotation", 0)) for s in slots if s.get("boardId")}

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

    # The board(s) not listed in `slots` are the entry/starting board (always unrotated); the rest
    # follow their `slots` order/rotation, mirroring the gate-attachment chain shown in the planner.
    ordered_board_ids = [b for b in board_order if b not in rotation_by_board] + [
        s["boardId"] for s in slots if s.get("boardId") in nodes_by_board
    ]

    boards_out: list[dict[str, Any]] = []
    for board_id in ordered_board_ids:
        rotation = rotation_by_board.get(board_id, 0)
        nodes_bool = [False] * NODES_LEN
        for loc in nodes_by_board.get(board_id, []):
            idx = _transform_flat_index(loc=loc, rotation=rotation)
            if 0 <= idx < NODES_LEN:
                nodes_bool[idx] = True

        glyph_id = next((gid for node_id, gid in glyphs.items() if node_id.startswith(board_id + "::")), None)

        boards_out.append({
            "Name": _infinitybuilds_named_slug(board_id, catalog.board_labels.get(board_id), class_slug),
            "Glyph": (
                _infinitybuilds_named_slug(glyph_id, catalog.glyph_labels.get(glyph_id), class_slug) if glyph_id else ""
            ),
            "Rotation": _rotation_info_quarter_turn(rotation),
            "Nodes": nodes_bool,
            "BoardId": board_id,
            "GlyphId": glyph_id,
        })

    return [boards_out] if boards_out else []
