import configparser
import logging
import re
from typing import TYPE_CHECKING

from PyQt6.QtCore import QSettings

from src.item.filter import Filter
from src.paragon.overlay.theme import BUILD_SOURCES, PLAYER_CLASSES
from src.paragon.transform import parse_rotation
from src.settings import get_settings

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pathlib import Path

    from src.paragon.overlay.contracts import BuildRow, OverlaySettings
    from src.profiles import ParagonBoardModel


def _params_ini_path() -> Path:
    """Return the user-specific params.ini path."""
    return get_settings().user_dir / "params.ini"


def _load_overlay_settings() -> OverlaySettings:
    """Load persisted overlay state from QSettings."""
    qs = QSettings("d4lf", "ParagonOverlay")

    # Migration trigger: Run if we haven't migrated yet.
    migration_done = str(qs.value("migration_done", "false")).lower() == "true"
    if not migration_done and _import_settings_from_ini(qs):
        qs.setValue("migration_done", "true")
        qs.sync()  # Force write to registry

    def parse_int(k: str) -> int | None:
        v = qs.value(k)
        if v is None:
            return None
        try:
            return int(v)
        except ValueError, TypeError:
            return None

    def parse_str(k: str) -> str | None:
        v = qs.value(k)
        return None if v is None else str(v)

    def parse_bool(k: str) -> bool | None:
        v = qs.value(k)
        if isinstance(v, bool):
            return v
        if v is None:
            return None
        # Handle potential string representations from legacy INI migration.
        v_str = str(v).lower()
        if v_str in ("true", "1", "yes", "on"):
            return True
        if v_str in ("false", "0", "no", "off"):
            return False
        return None

    return {
        "cell_size": parse_int("cell_size"),
        "profile": parse_str("profile"),
        "build_name": parse_str("build_name"),
        "build_idx": parse_int("build_idx"),
        "board_idx": parse_int("board_idx"),
        "grid_x": parse_int("grid_x"),
        "grid_y": parse_int("grid_y"),
        "is_collapsed": parse_bool("is_collapsed"),
        "cell_size_collapsed": parse_int("cell_size_collapsed"),
        "grid_x_collapsed": parse_int("grid_x_collapsed"),
        "grid_y_collapsed": parse_int("grid_y_collapsed"),
        "grid_locked": parse_bool("grid_locked"),
        "gold_frames": parse_bool("gold_frames"),
    }


def _save_overlay_settings(values: OverlaySettings) -> None:
    """Persist the current overlay state to QSettings."""
    qs = QSettings("d4lf", "ParagonOverlay")
    for k, v in values.items():
        if v is not None:
            qs.setValue(k, v)
    qs.sync()


def _import_settings_from_ini(qs: QSettings) -> bool:
    """Read legacy settings from params.ini and migrate them to QSettings."""
    ini = _params_ini_path()
    if not ini.exists():
        LOGGER.debug("Legacy paragon migration: params.ini not found at %s", ini)
        return False

    try:
        p = configparser.ConfigParser()
        read_files = p.read(ini, encoding="utf-8")
        if not read_files:
            return False

        if not p.has_section("paragon_overlay"):
            LOGGER.debug("Legacy paragon migration: No [paragon_overlay] section in %s", ini)
            return True

        sec = p["paragon_overlay"]
        for k in sec:
            qs.setValue(k, sec[k])

        # Clean up the INI file by removing the migrated section
        p.remove_section("paragon_overlay")
        with ini.open("w", encoding="utf-8") as f:
            p.write(f)

        LOGGER.info("Successfully migrated and cleaned up Paragon Overlay settings from %s", ini)
    except Exception:
        LOGGER.debug("Failed to migrate legacy Paragon Overlay settings", exc_info=True)
        return False
    else:
        return True


def _clamp_int(v: int | None, lo: int, hi: int, default: int) -> int:
    """Clamp an optional integer into a safe range, with a fallback default."""
    try:
        return max(lo, min(hi, int(v))) if v is not None else default
    except TypeError, ValueError:
        return default


def _format_build_display_name(raw_name: str | None) -> str:
    """Convert stored build/profile names into a cleaner title-card label."""
    text = str(raw_name or "").strip()
    if not text:
        return ""

    step_suffix = ""
    if step_match := re.search(r"(\s+-\s+Step\s+\d+)\s*$", text, flags=re.IGNORECASE):
        step_suffix = step_match.group(1)
        text = text[: step_match.start()].rstrip()

    parts = [re.sub(r"\s+", " ", part).strip(" _-") for part in text.split("_")]
    parts = [part for part in parts if part]

    if parts and parts[0].lower() in BUILD_SOURCES:
        parts = parts[1:]
    if parts and parts[0].lower() in PLAYER_CLASSES:
        parts = parts[1:]

    display_name = " ".join(parts).strip()
    if not display_name:
        display_name = re.sub(r"\s+", " ", text.replace("_", " ")).strip()

    return f"{display_name}{step_suffix}" if step_suffix else display_name


def _resolve_build_index(
    builds: list[BuildRow],
    *,
    profile_name: str | None = None,
    build_name: str | None = None,
    fallback_idx: int | None = None,
) -> int:
    """Resolve the selected build from persisted identifiers with index fallback."""
    if build_name:
        for idx, build in enumerate(builds):
            if build.get("name") != build_name:
                continue
            if profile_name and build.get("profile") != profile_name:
                continue
            return idx

    if profile_name:
        for idx, build in enumerate(builds):
            if build.get("profile") == profile_name:
                return idx

    return _clamp_int(fallback_idx, 0, max(0, len(builds) - 1), 0)


def load_builds_from_path(preset_path: str | None = None) -> list[BuildRow]:
    """Collect all available builds and flatten them into overlay-friendly rows.

    Each returned entry contains the visible build name, its board list, and the
    source profile name that is later used for grouping inside the popup.
    """
    _ = preset_path
    paragon_filters = Filter().get_paragon_filters()

    builds: list[BuildRow] = []
    for pname, payload in paragon_filters.items():
        steps = payload.paragon_boards_list
        bname = payload.name or "Unknown Build"
        # Newest step first keeps the build selector aligned with the latest
        # imported planner state while still exposing earlier progression steps.
        for idx in range(len(steps) - 1, -1, -1):
            sname = f"{bname} - Step {idx + 1}" if len(steps) > 1 else bname
            builds.append({"name": sname, "boards": steps[idx], "profile": pname})
    return builds


def format_board_display_text(board: ParagonBoardModel) -> str:
    """Build the readable label shown for a Paragon board card."""
    raw_name = str(board.name or "?")
    name_parts = raw_name.split("-", 1)
    class_slug = (name_parts[0] if name_parts else raw_name).strip().lower()
    board_slug = (name_parts[1] if len(name_parts) > 1 else raw_name).strip()
    class_name = {class_name: class_name.title() for class_name in PLAYER_CLASSES}.get(
        class_slug, class_slug.title() if class_slug else "?"
    )

    glyph_name = "No Glyph"
    if board.glyph:
        glyph_parts = str(board.glyph).strip().split("-", 1)
        glyph_slug = (
            glyph_parts[1]
            if len(glyph_parts) > 1 and glyph_parts[0].strip().lower() == class_slug
            else str(board.glyph).strip()
        )
        glyph_name = re.sub(r"[-_]+", " ", glyph_slug).strip().title() if glyph_slug else "No Glyph"

    readable_board = board_slug.replace("-", " ").strip().title() if board_slug else "?"
    return f"{class_name} - {readable_board} - {glyph_name} - {parse_rotation(board.rotation)}°"
