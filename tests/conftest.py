import sys
import typing

import pytest

from src.config.loader import IniConfigLoader
from src.config.settings_models import BrowserType

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture


# Skip Windows-only test modules on macOS
WINDOWS_ONLY_MODULES = [
    "read_descr_season6_tts_test.py",
    "read_descr_season8_tts_test.py",
    "read_descr_season_11_tts_test.py",
    "read_descr_season_12_tts_test.py",
    "read_descr_season_13_tts_test.py",
    "read_descr_tts_test.py",
    "filter_test.py",
    "template_finder_test.py",
    "char_inventory_test.py",
    "chest_test.py",
    "paragon_overlay_test.py",
]


def pytest_ignore_collect(collection_path, config):
    """Ignore Windows-only test files on macOS during collection."""
    if sys.platform == "darwin":
        # Check if the file is in our Windows-only list
        if collection_path.name in WINDOWS_ONLY_MODULES:
            return True
    return False


@pytest.fixture
def mock_ini_loader(mocker: MockerFixture):
    general_mock = mocker.patch.object(IniConfigLoader(), "_general")
    general_mock.language = "enUS"
    general_mock.browser = BrowserType.edge
    general_mock.full_dump = False
    return IniConfigLoader()
