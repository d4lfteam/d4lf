import sys
from pathlib import Path

BASE_DIR = (
    Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent.parent
)
ICON_PATH = BASE_DIR / "assets" / "logo.png"


def get_asset_path(filename: str) -> Path:
    """Find an asset in root/assets or src/assets, handling case sensitivity."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "assets" / filename

    # Search paths: 3 parents (root from gui/) and 2 parents (src from gui/).
    for parent_level in [2, 3]:
        base = Path(__file__).resolve().parents[parent_level]
        # Try exact name, then lowercase version.
        for name in [filename, filename.lower()]:
            path = base / "assets" / name
            if path.exists():
                return path
    # Fallback to the root path even if not found.
    return Path(__file__).resolve().parents[2] / "assets" / filename


DISCORD_ICON = get_asset_path("Discord.png")
GITHUB_ICON = get_asset_path("Github.png")
