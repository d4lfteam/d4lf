from __future__ import annotations

import datetime
import json
import logging
import re
import time
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from src import __version__
from src.config import BASE_DIR
from src.config.loader import IniConfigLoader

try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:  # pragma: no cover
    By = None  # type: ignore[assignment]
    WebDriverWait = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from pathlib import Path

    from selenium.webdriver.remote.webdriver import WebDriver


def _class_slug_from_name(class_name: str) -> str:
    class_name = (class_name or "").strip().lower()
    if not class_name or class_name == "unknown":
        return ""
    # normalize spaces/underscores
    return re.sub(r"[^a-z0-9\-]", "", re.sub(r"[\s_]+", "-", class_name))


def _prefix_with_class_slug(slug: str, class_slug: str) -> str:
    if not slug:
        return slug
    if not class_slug:
        return slug
    if slug.startswith(class_slug + "-"):
        return slug
    return f"{class_slug}-{slug}"


LOGGER = logging.getLogger(__name__)

GRID = 21
NODES_LEN = GRID * GRID


# ---------------------------------------------------------------------------
# Maxroll uses internal IDs for boards/glyphs. We keep the exported identifiers stable
# by resolving IDs to human-friendly names from data files (generated from d4data).
#
# Expected file (fallback to enUS):
#   assets/lang/<language>/paragon_maxroll_ids.json
# Format:
#   {"boards": {"<board_id>": "<display_name>", ...}, "glyphs": {"<glyph_id>": "<display_name>", ...}}
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_maxroll_name_maps() -> tuple[dict[str, str], dict[str, str]]:
    lang = IniConfigLoader().general.language
    candidates = (
        BASE_DIR / f"assets/lang/{lang}/paragon_maxroll_ids.json",
        BASE_DIR / "assets/lang/enUS/paragon_maxroll_ids.json",
    )

    for path in candidates:
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            continue
        except OSError:
            LOGGER.debug("Failed to read Maxroll paragon mapping file: %s", path, exc_info=True)
            continue

        if not isinstance(data, dict):
            continue

        boards = data.get("boards") or {}
        glyphs = data.get("glyphs") or {}
        if isinstance(boards, dict) and isinstance(glyphs, dict):
            boards_map = {str(k): str(v) for k, v in boards.items()}
            glyphs_map = {str(k): str(v) for k, v in glyphs.items()}
            return boards_map, glyphs_map

    return {}, {}


def _slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _maxroll_class_slug(board_id: str) -> str:
    # Example: "Paragon_Paladin_02" -> "paladin"
    m = re.match(r"^Paragon_([A-Za-z]+)_\d+$", board_id or "")
    return _slugify(m.group(1)) if m else ""


def _maxroll_board_slug(board_id: str) -> str:
    cls = _maxroll_class_slug(board_id)
    boards_map, _ = _load_maxroll_name_maps()
    name = boards_map.get(board_id, board_id)
    name_slug = _slugify(name)
    return f"{cls}-{name_slug}" if cls and name_slug else _slugify(board_id)


def _maxroll_glyph_slug(glyph_id: str, board_id: str) -> str:
    # We prefix with class for consistency with Mobalytics output.
    cls = _maxroll_class_slug(board_id)
    _, glyphs_map = _load_maxroll_name_maps()
    name = glyphs_map.get(glyph_id, glyph_id)
    name_slug = _slugify(name)
    return f"{cls}-{name_slug}" if cls and name_slug else _slugify(glyph_id)


def export_paragon_build_json(
    file_stem: str, build_name: str, source_url: str, paragon_boards_list: list[list[dict[str, Any]]]
) -> Path:
    """Write a D4Companion-compatible JSON containing Name + ParagonBoardsList.

    Output format is a JSON list with a single entry, so it can be consumed by tools that expect a list.
    """
    out_dir = IniConfigLoader().user_dir / "paragon"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{file_stem}.json"

    payload = [
        {
            "Name": build_name,
            "Source": source_url,
            "GeneratedAt": datetime.datetime.now(tz=datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "Generator": f"d4lf v{__version__}",
            "ParagonBoardsList": paragon_boards_list,
        }
    ]

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    LOGGER.info(f"Exported paragon JSON: {out_path}")
    return out_path


def extract_maxroll_paragon_steps(active_profile: dict[str, Any]) -> list[list[dict[str, Any]]]:
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

            nodes_dict = (bd or {}).get("nodes") or {}
            for loc_key in nodes_dict:
                try:
                    loc = int(loc_key)
                except TypeError, ValueError:
                    loc = None
                if loc is None:
                    continue
                idx = _transform_maxroll_location(loc=loc, rotation=rotation)
                if 0 <= idx < NODES_LEN:
                    nodes_bool[idx] = True

            boards_out.append({
                "Name": _maxroll_board_slug(board_id),
                "Glyph": _maxroll_glyph_slug(glyph_id, board_id) if glyph_id else "",
                "Rotation": _rotation_info_maxroll(rotation),
                "Nodes": nodes_bool,
                "BoardId": board_id,
                "GlyphId": glyph_id,
            })

        if boards_out:
            steps_out.append(boards_out)

    return steps_out


def extract_mobalytics_paragon_steps(variant: dict[str, Any]) -> list[list[dict[str, Any]]]:
    """Extract paragon boards from Mobalytics preloaded-state build variant.

    Matches the rotation + node-index transformation used in Diablo4Companion.
    """
    paragon = (variant or {}).get("paragon") or {}
    boards_data = paragon.get("boards") or []
    nodes_data = paragon.get("nodes") or []

    boards_out: list[dict[str, Any]] = []

    for board in boards_data:
        board_slug = ((board or {}).get("board") or {}).get("slug", "")
        board_slug = _fix_mobalytics_starting_board_slug(board_slug)

        glyph_slug = ((board or {}).get("glyph") or {}).get("slug", "")
        rotation = int((board or {}).get("rotation", 0))

        nodes_bool = [False] * NODES_LEN
        board_nodes = [
            n
            for n in nodes_data
            if isinstance(n, dict) and isinstance(n.get("slug"), str) and n["slug"].startswith(board_slug)
        ]

        for n in board_nodes:
            slug = n.get("slug", "")
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

            idx = _transform_xy_common(x=x, y=y, rotation_deg=rotation, base="mobalytics")
            if 0 <= idx < NODES_LEN:
                nodes_bool[idx] = True

        boards_out.append({
            "Name": board_slug,
            "Glyph": glyph_slug,
            "Rotation": _rotation_info_degrees(rotation),
            "Nodes": nodes_bool,
        })

    return [boards_out] if boards_out else []


def _parse_d4builds_paragon_boards(driver: WebDriver, class_slug: str) -> list[list[dict[str, Any]]]:
    """Parse D4Builds paragon boards from the currently loaded page."""
    boards_out: list[dict[str, Any]] = []

    try:
        board_elements = driver.find_elements(By.CLASS_NAME, "paragon__board")
    except Exception:
        LOGGER.debug("Failed to locate D4Builds paragon boards (continuing).", exc_info=True)
        board_elements = []

    for board_elem in board_elements:
        name_raw = ""
        lines: list[str] = []
        name_display = ""

        try:
            name_raw = board_elem.find_element(By.CLASS_NAME, "paragon__board__name").get_attribute("innerText") or ""
            lines = [ln.strip() for ln in name_raw.splitlines() if ln.strip()]
            # Prefer a line containing letters (sometimes line 1 is a numeric index)
            name_display = next((ln for ln in lines if any(ch.isalpha() for ch in ln)), (lines[0] if lines else ""))
        except Exception:
            name_display = ""

        # Try to infer a stable board id/slug from element attributes (best effort)
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

        name_slug = _prefix_with_class_slug(_slugify(board_id or name_display), class_slug)
        if not name_slug and lines and str(lines[0]).isdigit():
            name_slug = f"board-{lines[0]}"

        glyph_raw = ""
        try:
            glyph_elems = board_elem.find_elements(By.CLASS_NAME, "paragon__board__name__glyph")
            if glyph_elems:
                glyph_raw = (glyph_elems[0].get_attribute("innerText") or "").strip()
        except Exception:
            LOGGER.debug("Failed to read glyph name (continuing).", exc_info=True)

        glyph_display = glyph_raw.replace("(", "").replace(")", "").strip()
        glyph_slug = _prefix_with_class_slug(_slugify(glyph_display), class_slug)

        style_str = board_elem.get_attribute("style") or ""
        rotate_int = 0
        if "rotate(" in style_str:
            mm = re.search(r"rotate\(([-\d]+)deg\)", style_str)
            if mm:
                try:
                    rotate_int = int(mm.group(1)) % 360
                except Exception:
                    rotate_int = 0

        nodes = [False] * NODES_LEN

        try:
            tile_elems = board_elem.find_elements(By.CLASS_NAME, "paragon__board__tile")
        except Exception:
            tile_elems = []

        for tile in tile_elems:
            cls = tile.get_attribute("class") or ""
            if "active" not in cls:
                continue

            parts = [pp for pp in cls.split() if pp]
            # Example: "paragon__board__tile r2 c10 active enabled"
            r_part = next((x for x in parts if x.startswith("r")), "r0")
            c_part = next((x for x in parts if x.startswith("c")), "c0")

            try:
                r = int("".join(ch for ch in r_part if ch.isdigit()) or "0")
                c = int("".join(ch for ch in c_part if ch.isdigit()) or "0")
            except ValueError:
                continue

            # Transform coordinates based on rotation (matching Diablo4Companion)
            x = c
            y = r
            if rotate_int == 0:
                x = x - 1
                y = y - 1
            elif rotate_int == 90:
                x = GRID - r
                y = c - 1
            elif rotate_int == 180:
                x = GRID - c
                y = GRID - r
            elif rotate_int == 270:
                x = r - 1
                y = GRID - c

            if 0 <= x < GRID and 0 <= y < GRID:
                nodes[y * GRID + x] = True

        boards_out.append({
            "Name": name_slug or "paragon-board",
            "Glyph": glyph_slug,
            "Rotation": f"{rotate_int}°" if rotate_int in (0, 90, 180, 270) else "0°",
            "Nodes": nodes,
        })

    return [boards_out] if boards_out else []


def extract_d4builds_paragon_steps(
    driver: WebDriver, class_name: str = "", *, wait: WebDriverWait | None = None
) -> list[list[dict[str, Any]]]:
    """Extract paragon boards from D4Builds using Selenium.

    This reuses the existing Selenium session/page state created by the importer. We only
    click/wait for the Paragon tab if boards are not already present in the DOM.
    """
    class_slug = _class_slug_from_name(class_name)

    if By is None or WebDriverWait is None:  # pragma: no cover
        msg = "Selenium not available, cannot export D4Builds paragon"
        raise RuntimeError(msg)

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


# --- Helper functions (ported from Diablo4Companion) ---


def _rotation_info_maxroll(rot: int) -> str:
    return {0: "0°", 1: "90°", 2: "180°", 3: "270°"}.get(rot, "?°")


def _rotation_info_degrees(rot: int) -> str:
    rot = rot % 360
    return {0: "0°", 90: "90°", 180: "180°", 270: "270°"}.get(rot, "?°")


def _transform_maxroll_location(loc: int, rotation: int) -> int:
    """Transform a 0-based location index from Maxroll into the Nodes[] index.

    This follows the exact switch used in Diablo4Companion BuildsManagerMaxroll.
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


def _transform_xy_common(x: int, y: int, rotation_deg: int, base: str) -> int:
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


def _fix_mobalytics_starting_board_slug(board_slug: str) -> str:
    # Fix naming inconsistency (ported from Diablo4Companion)
    return (
        board_slug
        .replace("barbarian-starter-board", "barbarian-starting-board")
        .replace("druid-starter-board", "druid-starting-board")
        .replace("necromancer-starter-board", "necromancer-starting-board")
        .replace("paladin-starter-board", "paladin-starting-board")
        .replace("rogue-starter-board", "rogue-starting-board")
        .replace("sorcerer-starter-board", "sorcerer-starting-board")
        .replace("spiritborn-starter-board", "spiritborn-starting-board")
    )
