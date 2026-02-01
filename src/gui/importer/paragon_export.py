from __future__ import annotations

import datetime
import json
import logging
import re
import time
from typing import TYPE_CHECKING, Any

from src import __version__
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
# Maxroll ID -> human friendly names (ported from Diablo4Companion data files).
# Used to export Paragon JSON with readable identifiers (similar to Mobalytics).
# ---------------------------------------------------------------------------

_MAXROLL_BOARD_ID_TO_NAME = {
    "Paragon_Barb_00": "Start",
    "Paragon_Barb_01": "Hemorrhage",
    "Paragon_Barb_02": "Blood Rage",
    "Paragon_Barb_03": "Carnage",
    "Paragon_Barb_04": "Decimator",
    "Paragon_Barb_05": "Bone Breaker",
    "Paragon_Barb_06": "Flawless Technique",
    "Paragon_Barb_07": "Warbringer",
    "Paragon_Barb_08": "Weapons Master",
    "Paragon_Barb_10": "Force of Nature",
    "Paragon_Druid_00": "Start",
    "Paragon_Druid_01": "Thunderstruck",
    "Paragon_Druid_02": "Earthen Devastation",
    "Paragon_Druid_03": "Survival Instincts",
    "Paragon_Druid_04": "Lust for Carnage",
    "Paragon_Druid_05": "Heightened Malice",
    "Paragon_Druid_06": "Inner Beast",
    "Paragon_Druid_07": "Constricting Tendrils",
    "Paragon_Druid_08": "Ancestral Guidance",
    "Paragon_Druid_10": "Untamed",
    "Paragon_Necro_00": "Start",
    "Paragon_Necro_01": "Cult Leader",
    "Paragon_Necro_02": "Hulking Monstrosity",
    "Paragon_Necro_03": "Flesh-eater",
    "Paragon_Necro_04": "Scent of Death",
    "Paragon_Necro_05": "Bone Graft",
    "Paragon_Necro_06": "Blood Begets Blood",
    "Paragon_Necro_07": "Bloodbath",
    "Paragon_Necro_08": "Wither",
    "Paragon_Necro_10": "Frailty",
    "Paragon_Paladin_00": "Start",
    "Paragon_Paladin_01": "Castle",
    "Paragon_Paladin_02": "Shield Bearer",
    "Paragon_Paladin_03": "Fervent",
    "Paragon_Paladin_04": "Preacher",
    "Paragon_Paladin_05": "Divinity",
    "Paragon_Paladin_06": "Relentless",
    "Paragon_Paladin_07": "Sentencing",
    "Paragon_Paladin_08": "Endure",
    "Paragon_Paladin_09": "Beacon",
    "Paragon_Rogue_00": "Start",
    "Paragon_Rogue_01": "Eldritch Bounty",
    "Paragon_Rogue_02": "Tricks of the Trade",
    "Paragon_Rogue_03": "Cheap Shot",
    "Paragon_Rogue_04": "Deadly Ambush",
    "Paragon_Rogue_05": "Leyrana's Instinct",
    "Paragon_Rogue_06": "No Witnesses",
    "Paragon_Rogue_07": "Exploit Weakness",
    "Paragon_Rogue_08": "Cunning Stratagem",
    "Paragon_Rogue_10": "Danse Macabre",
    "Paragon_Sorc_00": "Start",
    "Paragon_Sorc_01": "Searing Heat",
    "Paragon_Sorc_02": "Frigid Fate",
    "Paragon_Sorc_03": "Static Surge",
    "Paragon_Sorc_04": "Elemental Summoner",
    "Paragon_Sorc_05": "Burning Instinct",
    "Paragon_Sorc_06": "Icefall",
    "Paragon_Sorc_07": "Ceaseless Conduit",
    "Paragon_Sorc_08": "Enchantment Master",
    "Paragon_Sorc_10": "Fundamental Release",
    "Paragon_Spirit_0": "Start",
    "Paragon_Spirit_01": "In-Fighter",
    "Paragon_Spirit_02": "Spiney Skin",
    "Paragon_Spirit_03": "Viscous Shield",
    "Paragon_Spirit_04": "Bitter Medicine",
    "Paragon_Spirit_05": "Revealing",
    "Paragon_Spirit_06": "Drive",
    "Paragon_Spirit_07": "Convergence",
    "Paragon_Spirit_08": "Sapping",
}

_MAXROLL_GLYPH_ID_TO_NAME = {
    "Rare_001_Intelligence_Main": "Enchanter",
    "Rare_002_Intelligence_Main": "Unleash",
    "Rare_003_Intelligence_Main": "Elementalist",
    "Rare_004_Intelligence_Main": "Adept",
    "Rare_005_Intelligence_Main": "Conjurer",
    "Rare_006_Intelligence_Main": "Charged",
    "Rare_007_Willpower_Side": "Torch",
    "Rare_008_Willpower_Side": "Pyromaniac",
    "Rare_009_Willpower_Side": "Cryopathy",
    "Rare_010_Dexterity_Main": "Tactician",
    "Rare_011_Intelligence_Side": "Guzzler",
    "Rare_011_Willpower_Side": "Imbiber",
    "Rare_012_Intelligence_Side": "Protector",
    "Rare_012_Willpower_Side": "Reinforced",
    "Rare_013_Dexterity_Side": "Poise",
    "Rare_014_Dexterity_Side": "Territorial",
    "Rare_014_Strength_Main": "Turf",
    "Rare_014_Strength_Side": "Turf",
    "Rare_015_Dexterity_Side": "Flamefeeder",
    "Rare_016_Dexterity_Side": "Exploit",
    "Rare_016_Intelligence_Side": "Exploit",
    "Rare_016_Strength_Side": "Exploit",
    "Rare_017_Dexterity_Side": "Winter",
    "Rare_018_Dexterity_Side": "Electrocute",
    "Rare_019_Dexterity_Side": "Destruction",
    "Rare_020_Dexterity_Side": "Control",
    "Rare_020_Intelligence_Main": "Control",
    "Rare_020_Intelligence_Side": "Control",
    "Rare_021_Strength_Main": "Ambidextrous",
    "Rare_022_Strength_Main": "Might",
    "Rare_023_Strength_Main": "Cleaver",
    "Rare_024_Strength_Main": "Seething",
    "Rare_025_Strength_Main": "Crusher",
    "Rare_026_Strength_Main": "Executioner",
    "Rare_027_Strength_Main": "Ire",
    "Rare_028_Strength_Main": "Marshal",
    "Rare_029_Dexterity_Side": "Bloodfeeder",
    "Rare_030_Dexterity_Side": "Wrath",
    "Rare_031_Dexterity_Side": "Weapon Master",
    "Rare_032_Dexterity_Side": "Mortal Draw",
    "Rare_033_Intelligence_Side": "Revenge",
    "Rare_033_Willpower_Side": "Revenge",
    "Rare_033_Willpower_Side_Necro": "Revenge",
    "Rare_034_Intelligence_Side": "Undaunted",
    "Rare_034_Willpower_Side": "Undaunted",
    "Rare_035_Intelligence_Side": "Dominate",
    "Rare_035_Willpower_Side": "Dominate",
    "Rare_035_Willpower_Side_Necro": "Dominate",
    "Rare_036_Willpower_Side": "Disembowel",
    "Rare_037_Willpower_Side": "Brawl",
    "Rare_038_Intelligence_Main": "Corporeal",
    "Rare_039_Willpower_Main": "Fang and Claw",
    "Rare_040_Willpower_Main": "Earth and Sky",
    "Rare_041_Intelligence_Side": "Wilds",
    "Rare_042_Willpower_Main": "Werebear",
    "Rare_043_Willpower_Main": "Werewolf",
    "Rare_044_Willpower_Main": "Human",
    "Rare_045_Intelligence_Side": "Bane",
    "Rare_045_Strength_Side": "Bane",
    "Rare_046_Dexterity_Side": "Abyssal",
    "Rare_046_Intelligence_Side": "Keeper",
    "Rare_047_Dexterity_Side": "Fulminate",
    "Rare_047_Intelligence_Side": "Fulminate",
    "Rare_048_Dexterity_Side": "Tracker",
    "Rare_048_Intelligence_Side": "Tracker",
    "Rare_049_Dexterity_Side": "Outmatch",
    "Rare_049_Strength_Main": "Outmatch",
    "Rare_049_Strength_Side": "Outmatch",
    "Rare_050_Dexterity_Main": "Spirit",
    "Rare_050_Dexterity_Side": "Spirit",
    "Rare_050_Willpower_Side": "Spirit",
    "Rare_051_Dexterity_Side": "Shapeshifter",
    "Rare_052_Dexterity_Main": "Versatility",
    "Rare_053_Dexterity_Main": "Closer",
    "Rare_054_Dexterity_Main": "Ranger",
    "Rare_055_Dexterity_Main": "Chip",
    "Rare_055_Dexterity_Side": "Chip",
    "Rare_055_Willpower_Side": "Chip",
    "Rare_056_Dexterity_Main": "Frostfeeder",
    "Rare_057_Dexterity_Main": "Fluidity",
    "Rare_058_Intelligence_Side": "Infusion",
    "Rare_059_Dexterity_Main": "Devious",
    "Rare_060_Dexterity_Side": "Warrior",
    "Rare_061_Intelligence_Side": "Combat",
    "Rare_062_Dexterity_Side": "Gravekeeper",
    "Rare_063_Intelligence_Side": "Canny",
    "Rare_064_Intelligence_Side": "Efficacy",
    "Rare_065_Intelligence_Side": "Snare",
    "Rare_066_Dexterity_Side": "Essence",
    "Rare_067_Strength_Side": "Pride",
    "Rare_068_Strength_Side": "Ambush",
    "Rare_069_Intelligence_Main": "Sacrificial",
    "Rare_070_Intelligence_Main": "Blood-drinker",
    "Rare_071_Intelligence_Main": "Deadraiser",
    "Rare_072_Intelligence_Main": "Mage",
    "Rare_073_Intelligence_Main": "Amplify",
    "Rare_074_Willpower_Side": "Golem",
    "Rare_075_Willpower_Side": "Scourge",
    "Rare_076_Strength_Main": "Diminish",
    "Rare_076_Strength_Side": "Diminish",
    "Rare_077_Willpower_Side": "Warding",
    "Rare_078_Willpower_Side": "Darkness",
    "Rare_079_Dexterity_Side": "Exploit",
    "Rare_080_Strength_Main": "Twister",
    "Rare_081_Strength_Main": "Rumble",
    "Rare_082_Dexterity_Main": "Explosive",
    "Rare_083_Intelligence_Side": "Nightstalker",
    "Rare_084_Intelligence_Main": "Stalagmite",
    "Rare_085_Dexterity_Side": "Invocation",
    "Rare_086_Dexterity_Side": "Tectonic",
    "Rare_087_Willpower_Main": "Electrocution",
    "Rare_088_Intelligence_Main": "Exhumation",
    "Rare_089_Willpower_Side": "Desecration",
    "Rare_090_Dexterity_Main": "Menagerist",
    "Rare_091_Strength_Side": "Hone",
    "Rare_092_Intelligence_Side": "Consumption",
    "Rare_093_Dexterity_Main": "Fitness",
    "Rare_094_Intelligence_Side": "Ritual",
    "Rare_095_Dexterity_Main": "Jagged Plume",
    "Rare_096_Strength_Side": "Innate",
    "Rare_097_Dexterity_Main": "Wildfire",
    "Rare_098_Strength_Side": "Colossal",
    "Rare_100_Dexterity_Main": "Talon",
    "Rare_101_Strength_Side": "Hubris",
    "Rare_102_Dexterity_Main": "Fester",
    "Rare_103_Strength_Main": "Sentinel",
    "Rare_104_Dexterity_Side": "Honed",
    "Rare_105_Strength_Main": "Law",
    "Rare_106_Willpower_Side": "Arbiter ",
    "Rare_107_Strength_Main": "Resplendence",
    "Rare_108_Intelligence_Side": "Judicator",
    "Rare_109_Dexterity_Side": "Feverous",
    "Rare_110_Strength_Main": "Apostle",
    "Rare_Dex_Generic": "Headhunter",
    "Rare_Int_Generic": "Eliminator",
    "Rare_Str_Generic": "Challenger",
    "Rare_Will_Generic": "Headhunter",
}


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
    name = _MAXROLL_BOARD_ID_TO_NAME.get(board_id, board_id)
    name_slug = _slugify(name)
    return f"{cls}-{name_slug}" if cls and name_slug else _slugify(board_id)


def _maxroll_glyph_slug(glyph_id: str, board_id: str) -> str:
    # We prefix with class for consistency with Mobalytics output.
    cls = _maxroll_class_slug(board_id)
    name = _MAXROLL_GLYPH_ID_TO_NAME.get(glyph_id, glyph_id)
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
