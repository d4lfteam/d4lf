import sys
import typing

import pytest

from src.config.loader import IniConfigLoader
from src.config.settings_models import BrowserType

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

# Skip Windows-only test modules on non-Windows platforms
WINDOWS_ONLY_MODULES = ["info_overlay_test.py", "paragon_overlay_test.py", "test_sigils_tab.py", "ui_thread_test.py"]


def pytest_ignore_collect(collection_path, config):
    """Ignore Windows-only test files on non-Windows platforms during collection."""
    if sys.platform != "win32":
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
