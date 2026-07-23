"""Application-owned packaged assets."""

import sys
from pathlib import Path

BASE_DIR = (
    Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent.parent
)


def get_asset_path(filename: str) -> Path:
    """Find a packaged asset, including the lowercase names used by releases."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "assets" / filename
    for parent_level in (2, 3):
        base = Path(__file__).resolve().parents[parent_level]
        for name in (filename, filename.lower()):
            path = base / "assets" / name
            if path.exists():
                return path
    return Path(__file__).resolve().parents[2] / "assets" / filename


ICON_PATH = get_asset_path("logo.png")
DISCORD_ICON = get_asset_path("Discord.png")
GITHUB_ICON = get_asset_path("Github.png")
