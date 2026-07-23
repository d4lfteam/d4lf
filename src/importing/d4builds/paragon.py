import logging
import re
import time
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from src.importing.paragon import class_prefixed_slug
from src.paragon import NODES_LEN
from src.paragon import class_slug_from_name as _class_slug_from_name
from src.paragon import rotation_info_degrees as _rotation_info_degrees
from src.paragon import transform_xy as _transform_xy

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver


LOGGER = logging.getLogger(__name__)


def _parse_d4builds_paragon_boards(driver: WebDriver, class_slug: str) -> list[list[dict[str, Any]]]:
    """Parse D4Builds paragon boards from the currently loaded page."""
    boards_out: list[dict[str, Any]] = []
    try:
        board_elements = driver.find_elements(By.CLASS_NAME, "paragon__board")
    except Exception:
        LOGGER.debug("Failed to read D4Builds paragon board elements.", exc_info=True)
        board_elements = []
    for board_elem in board_elements:
        name_raw = ""
        lines: list[str] = []
        try:
            name_raw = board_elem.find_element(By.CLASS_NAME, "paragon__board__name").get_attribute("innerText") or ""
            lines = [line.strip() for line in name_raw.splitlines() if line.strip()]
            name_display = next(
                (line for line in lines if any(ch.isalpha() for ch in line)), (lines[0] if lines else "")
            )
        except Exception:
            LOGGER.debug("Failed to read D4Builds board name.", exc_info=True)
            name_display = ""
        board_id = ""
        try:
            attrs = driver.execute_script(
                "var a=arguments[0].attributes; var o={}; for (var i=0;i<a.length;i++){o[a[i].name]=a[i].value}; return o;",
                board_elem,
            )
            if isinstance(attrs, dict):
                for key in ("data-board", "data-board-id", "data-id", "data-name", "data-board-name", "data-boardname"):
                    value = attrs.get(key)
                    if isinstance(value, str) and value.strip():
                        board_id = value.strip()
                        break
                if not board_id:
                    for value in attrs.values():
                        if (
                            isinstance(value, str)
                            and re.fullmatch(r"[A-Za-z0-9_-]{3,64}", value.strip())
                            and "-" in value
                        ):
                            board_id = value.strip()
                            break
        except Exception:
            LOGGER.debug("Failed to infer board id (continuing).", exc_info=True)
        name_slug = class_prefixed_slug(board_id or name_display, class_slug)
        if not name_slug and lines and lines[0].isdigit():
            name_slug = f"board-{lines[0]}"
        glyph_raw = ""
        try:
            glyph_elems = board_elem.find_elements(By.CLASS_NAME, "paragon__board__name__glyph")
            if glyph_elems:
                glyph_raw = (glyph_elems[0].get_attribute("innerText") or "").strip()
        except Exception:
            LOGGER.debug("Failed to read glyph name (continuing).", exc_info=True)
        glyph_slug = class_prefixed_slug((glyph_raw or "").replace("(", "").replace(")", "").strip(), class_slug)
        style_str = board_elem.get_attribute("style") or ""
        rotate_int = 0
        if "rotate(" in style_str:
            match = re.search(r"rotate\(([-\d]+)deg\)", style_str)
            if match:
                with suppress(ValueError):
                    rotate_int = int(match.group(1)) % 360
        nodes = [False] * NODES_LEN
        try:
            tile_elems = board_elem.find_elements(By.CLASS_NAME, "paragon__board__tile")
        except Exception:
            LOGGER.debug("Failed to read D4Builds board tiles (continuing).", exc_info=True)
            tile_elems = []
        for tile in tile_elems:
            classes = tile.get_attribute("class") or ""
            if "active" not in classes:
                continue
            parts = classes.split()
            row = next((part for part in parts if part.startswith("r")), "r0")
            column = next((part for part in parts if part.startswith("c")), "c0")
            r = int("".join(ch for ch in row if ch.isdigit()) or "0")
            c = int("".join(ch for ch in column if ch.isdigit()) or "0")
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
    """Extract paragon boards from D4Builds using Selenium."""
    class_slug = _class_slug_from_name(class_name)
    wait = wait or WebDriverWait(driver, 10)
    try:
        if driver.find_elements(By.CLASS_NAME, "paragon__board"):
            return _parse_d4builds_paragon_boards(driver, class_slug)
    except Exception:
        LOGGER.debug("Could not query for existing D4Builds paragon boards (continuing).", exc_info=True)
    try:
        wait.until(lambda d: len(d.find_elements(By.CLASS_NAME, "builder__navigation__link")) > 0)
    except Exception:
        LOGGER.debug("Timed out waiting for D4Builds navigation links (continuing).", exc_info=True)
    try:
        nav_links = driver.find_elements(By.CLASS_NAME, "builder__navigation__link")
        if len(nav_links) >= 3:
            driver.execute_script("arguments[0].click();", nav_links[2])
        else:
            element = driver.find_element(By.XPATH, "//*[contains(normalize-space(.), 'Paragon')]")
            driver.execute_script("arguments[0].click();", element)
        time.sleep(0.25)
    except Exception:
        LOGGER.debug("Could not click Paragon tab (continuing).", exc_info=True)
    try:
        wait.until(lambda d: len(d.find_elements(By.CLASS_NAME, "paragon__board")) > 0)
    except Exception:
        LOGGER.debug("Timed out waiting for D4Builds paragon boards (continuing).", exc_info=True)
    return _parse_d4builds_paragon_boards(driver, class_slug)
