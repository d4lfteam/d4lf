from pathlib import Path

from src.app.assets import DISCORD_ICON, GITHUB_ICON, ICON_PATH, get_asset_path


def test_asset_paths_are_paths() -> None:
    assert all(isinstance(path, Path) for path in (DISCORD_ICON, GITHUB_ICON, ICON_PATH))


def test_get_asset_path_resolves_relative_asset() -> None:
    assert get_asset_path("missing.png").name == "missing.png"
