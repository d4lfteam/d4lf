import pytest

from src.desktop import DISCORD_ICON, GITHUB_ICON, ICON_PATH, get_asset_path


@pytest.mark.parametrize("path", [ICON_PATH, DISCORD_ICON, GITHUB_ICON])
def test_packaged_asset_paths_point_to_existing_files(path) -> None:
    assert path.is_file()


def test_get_asset_path_resolves_relative_asset() -> None:
    assert get_asset_path("missing.png").name == "missing.png"
